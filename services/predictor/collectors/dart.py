"""DART(전자공시) Open API — 대량보유상황보고서(5%룰 지분공시) 조회.

무료 공식 API(opendart.fss.or.kr, 회원가입 후 인증키 발급). 실측 확인
(2026-08-08, 실제 키로 검증): 요청 자체는 잘 되지만, `pblntf_detail_ty`
파라미터가 API에서 전혀 필터링을 안 함 — D001~D005 아무 값이나 넣어도
(심지어 생략해도) 결과가 완전히 동일했음(전부 total_count=937). pblntf_ty=D
(지분공시)로 조회하면 대량보유상황보고서와 완전히 다른 유형인 "임원·주요
주주 소유상황보고서"까지 섞여서 옴 — 이것 때문에 첫 구현에서 관련없는
회사까지 다 처리하려다 타임아웃 남. 대신 `report_nm` 필드에 실제 보고서명이
그대로 찍혀나오는 걸 확인해서, "대량보유상황보고서"라는 문자열이 포함된
것만 클라이언트에서 걸러낸다.

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

_PBLNTF_TY = "D"  # 지분공시 (실측 확인: detail_ty는 API에서 안 먹혀서 안 씀)
_MAJOR_HOLDER_REPORT_MARKER = "대량보유상황보고서"


def list_recent_major_holder_filings(bgn_de: str, end_de: str) -> list[dict]:
    """`bgn_de`~`end_de`(YYYYMMDD) 사이 접수된 대량보유상황보고서만 골라
    돌려준다 (지분공시 카테고리 전체를 받은 뒤 report_nm으로 클라이언트
    필터링 — 위 docstring 참고). 반환 항목엔 corp_code(8자리 DART 고유
    번호), rcept_no, corp_name, stock_code, flr_nm(제출인명), rcept_dt,
    report_nm이 있다. 페이지네이션(최대 100건/페이지) 처리 포함.
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
        results.extend(
            item for item in page_list
            if _MAJOR_HOLDER_REPORT_MARKER in item.get("report_nm", "")
        )

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


# 사모펀드/PE·VC로 추정되는 보고자명(제출인명) 패턴. 실측 확인(2026-08-08,
# 최근 1주일 실제 보고자 60여 건 직접 확인): "사모투자합자회사" 같은 엄격한
# 법적 명칭만으로는 거의 안 걸린다 — 실제로는 "OO인베스트먼트", "OO아이비
# 투자"(IB투자=벤처캐피탈), "OO파트너스", "OO캐피탈" 형태가 훨씬 흔했다.
# 그래서 범위를 넓혔음 — 대신 "인베스트먼트/파트너스/캐피탈/자산운용"류는
# 일반 자산운용사(국민연금 위탁운용 등)도 걸릴 수 있어 완벽한 판별이
# 아니다. UI에 반드시 "패턴 기반 추정"이라고 명시할 것(정직하게 표시).
_PEF_NAME_MARKERS = [
    "사모투자합자회사",
    "사모투자전문회사",
    "사모투자합자조합",
    "기업재무안정",
    "사모집합투자기구",
    "경영참여형",
    "프라이빗에쿼티",
    "PEF",
    "인베스트먼트",
    "아이비투자",
    "파트너스",
    "캐피탈",
    "벤처투자",
    "사모",
]


def looks_like_pef(reporter_name: str) -> bool:
    """제출인명이 사모펀드/SPC로 보이는지 패턴으로 추정한다.
    완벽한 판별이 아니므로 UI에 반드시 "추정"이라고 표시할 것."""
    return any(marker in reporter_name for marker in _PEF_NAME_MARKERS)
