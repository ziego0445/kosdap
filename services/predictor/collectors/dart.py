"""DART(전자공시) Open API — 대량보유상황보고서(5%룰 지분공시) 조회.

무료 공식 API(opendart.fss.or.kr, 회원가입 후 인증키 발급). 실측 확인
(2026-08-08): 요청 형식은 검증됨(더미 키로 "010 등록되지 않은 인증키"라는
정상 에러 응답을 받아 URL/파라미터가 맞다는 걸 확인) — 실제 키로 데이터
자체를 받는 건 아직 미검증, DART_API_KEY가 설정되면 검증할 것.

주의: 이 API가 주는 필드에는 "취득단가(평단가)"가 없다 — 그래서
pef_tracker.py는 "얼마나 샀는지(증감량)"만 다루고 "PEF 평단가 대비 현재가"
같은 가격비교 로직은 만들지 않는다(그 정보 자체가 구조화 데이터로 없음).
"""

from __future__ import annotations

import logging

import requests

from config import DART_API_KEY

logger = logging.getLogger(__name__)

_LIST_URL = "https://opendart.fss.or.kr/api/list.json"
_MAJOR_STOCK_URL = "https://opendart.fss.or.kr/api/majorstock.json"

# 대량보유상황보고서 필터 코드 (opendart 개발가이드 DS001 확인, 2026-08-08)
_PBLNTF_TY = "D"
_PBLNTF_DETAIL_TY = "D001"


def list_recent_major_holder_filings(bgn_de: str, end_de: str) -> list[dict]:
    """`bgn_de`~`end_de`(YYYYMMDD) 사이 접수된 대량보유상황보고서 전체를
    회사 구분 없이 검색한다. 반환 항목엔 corp_code(8자리 DART 고유번호),
    rcept_no, corp_name, stock_code, flr_nm(제출인명), rcept_dt가 있다.
    페이지네이션(최대 100건/페이지) 처리 포함.
    """
    if not DART_API_KEY:
        logger.warning("DART_API_KEY 미설정 — PEF 지분공시 수집 건너뜀")
        return []

    results: list[dict] = []
    page_no = 1
    while True:
        try:
            resp = requests.get(
                _LIST_URL,
                params={
                    "crtfc_key": DART_API_KEY,
                    "bgn_de": bgn_de,
                    "end_de": end_de,
                    "pblntf_ty": _PBLNTF_TY,
                    "pblntf_detail_ty": _PBLNTF_DETAIL_TY,
                    "page_no": page_no,
                    "page_count": 100,
                },
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            logger.exception("DART list.json 조회 실패 (page=%d)", page_no)
            break

        status = data.get("status")
        if status == "013":  # 조회된 데이터가 없습니다 — 정상 케이스(그 기간에 공시 없음)
            break
        if status != "000":
            logger.error("DART list.json 오류: %s %s", status, data.get("message"))
            break

        page_list = data.get("list", [])
        results.extend(page_list)

        total_page = data.get("total_page", 1)
        if page_no >= total_page:
            break
        page_no += 1

    return results


def fetch_major_holder_detail(corp_code: str) -> list[dict]:
    """특정 회사(corp_code, 8자리)의 대량보유 상황보고 이력 전체.
    항목별 repror(대표보고자), stkqy_irds(보유주식 증감), stkrt_irds(보유
    비율 증감), report_resn(보고사유), rcept_dt를 준다."""
    if not DART_API_KEY:
        return []
    try:
        resp = requests.get(
            _MAJOR_STOCK_URL,
            params={"crtfc_key": DART_API_KEY, "corp_code": corp_code},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.exception("DART majorstock.json 조회 실패 (corp_code=%s)", corp_code)
        return []

    if data.get("status") != "000":
        return []
    return data.get("list", [])


# 사모펀드/SPC로 추정되는 보고자명(제출인명) 패턴 — 보수적으로(오탐보다는
# 누락을 택함) 잡는다. 정식 GP 등록명단 DB는 아니라 완벽하지 않음 — 화면에
# "패턴 기반 추정"이라고 명시할 것 (docs 참고, 정직하게 표시하는 게 원칙).
_PEF_NAME_MARKERS = [
    "사모투자합자회사",
    "사모투자전문회사",
    "기업재무안정",
    "사모투자합자조합",
    "PEF",
    "사모집합투자기구",
    "경영참여형",
]


def looks_like_pef(reporter_name: str) -> bool:
    """제출인명이 사모펀드/SPC로 보이는지 패턴으로 추정한다.
    완벽한 판별이 아니므로 UI에 반드시 "추정"이라고 표시할 것."""
    return any(marker in reporter_name for marker in _PEF_NAME_MARKERS)
