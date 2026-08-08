"""사모펀드(PEF) 최근 지분 매수 랭킹.

DART 대량보유상황보고서(5%룰)를 스캔해서, 제출인명이 사모펀드/SPC로
보이는(collectors/dart.looks_like_pef) 보고 건만 골라 최근 순매수량 순으로
정렬한다. "평단가 대비 현재가" 같은 가격비교/매수매도 시그널은 만들지
않는다 — DART API에 취득단가 필드 자체가 없어서(2026-08-08 실측 확인)
정확히 계산할 수 없는 값을 억지로 추정하지 않기 위함(kosdap 전체 원칙).

즉 이 모듈이 만드는 건 순수하게 "최근 N일간 사모펀드로 추정되는 보고자가
지분을 늘린 회사 랭킹"이라는 객관적 사실 나열이지, 투자 조언이 아니다.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

from collectors.dart import (
    fetch_major_holder_detail,
    list_recent_major_holder_filings,
    looks_like_pef,
)
from collectors.market_hours import KST

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent / "data"
_OUTPUT_PATH = _DATA_DIR / "pef_activity.json"

_LOOKBACK_DAYS = 30  # 5%룰 공시는 드문 이벤트라 넉넉히 한 달치를 본다


def _parse_number(raw: str | None) -> float:
    """DART 숫자 필드는 "1,234,567" / "-" / "" 형태로 온다."""
    if not raw or raw == "-":
        return 0.0
    try:
        return float(raw.replace(",", ""))
    except ValueError:
        return 0.0


def _normalize_date(raw: str) -> str:
    """비교용으로만 쓴다 — list.json은 YYYYMMDD, majorstock.json은
    YYYY-MM-DD로 rcept_dt 포맷이 서로 다르다는 걸 실측으로 발견함
    (2026-08-08). 이것 때문에 처음엔 날짜 필터가 항상 어긋나서 결과가
    0건이었음 — 하이픈을 지워서 같은 포맷으로 맞춘다."""
    return raw.replace("-", "")


def collect_pef_activity() -> list[dict]:
    end = dt.datetime.now(KST).date()
    start = end - dt.timedelta(days=_LOOKBACK_DAYS)
    bgn_de, end_de = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

    filings = list_recent_major_holder_filings(bgn_de, end_de)
    if not filings:
        return []

    # 회사당 상세조회(majorstock.json)는 네트워크 왕복이 있어(실측 ~0.7초/건)
    # 전체 회사를 다 부르면 느리다(30일치는 수백~천 개 회사) — list.json
    # 응답에 이미 제출인명(flr_nm)이 있으므로, 그걸로 먼저 PEF로 보이는
    # 회사만 걸러내고 그 회사들만 상세조회한다 (2026-08-08 실측으로
    # 병목 확인 후 최적화: 전체 회사 조회 시 30일치가 9분 가까이 걸렸음).
    pef_candidate_filings = [f for f in filings if looks_like_pef(f.get("flr_nm", ""))]
    companies = {f["corp_code"]: f for f in pef_candidate_filings if f.get("corp_code")}
    logger.info(
        "DART 대량보유상황보고서: 전체 %d건 중 PEF로 추정되는 제출인 %d건 -> %d개 회사 상세조회 (최근 %d일)",
        len(filings), len(pef_candidate_filings), len(companies), _LOOKBACK_DAYS,
    )

    rows: list[dict] = []
    for corp_code, meta in companies.items():
        history = fetch_major_holder_detail(corp_code)
        pef_net_buy = 0.0
        pef_reporters: set[str] = set()
        latest_report_reason = None
        latest_date = None
        latest_date_norm = None

        for entry in history:
            rcept_dt = entry.get("rcept_dt", "")
            rcept_dt_norm = _normalize_date(rcept_dt)
            if not (bgn_de <= rcept_dt_norm <= end_de):
                continue
            reporter = entry.get("repror", "")
            if not looks_like_pef(reporter):
                continue

            delta = _parse_number(entry.get("stkqy_irds"))
            pef_net_buy += delta
            pef_reporters.add(reporter)
            if latest_date_norm is None or rcept_dt_norm > latest_date_norm:
                latest_date_norm = rcept_dt_norm
                latest_date = rcept_dt
                latest_report_reason = entry.get("report_resn")

        if pef_reporters:  # 이 회사에 PEF로 추정되는 보고자가 하나라도 있었으면만 기록
            rows.append(
                {
                    "corpCode": corp_code,
                    "corpName": meta.get("corp_name"),
                    "stockCode": meta.get("stock_code"),
                    "pefNetBuyShares": round(pef_net_buy),
                    "pefReporters": sorted(pef_reporters),
                    "latestReportDate": latest_date,
                    "latestReportReason": latest_report_reason,
                }
            )

    rows.sort(key=lambda r: r["pefNetBuyShares"], reverse=True)
    return rows


def export_pef_activity() -> None:
    """수집 + git 커밋 파일(services/predictor/data/pef_activity.json) 저장.
    accuracy_log.py와 같은 패턴 — 원본은 git에 커밋되고, apps/web/public
    쪽 브리지 파일은 main.py가 빌드마다 복사해서 만든다."""
    rows = collect_pef_activity()
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _OUTPUT_PATH.write_text(
            json.dumps(
                {
                    "generatedAt": dt.datetime.now(dt.UTC).isoformat(),
                    "lookbackDays": _LOOKBACK_DAYS,
                    "rows": rows,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info("PEF 활동 랭킹 저장: %s (%d개 회사)", _OUTPUT_PATH, len(rows))
    except Exception:
        logger.exception("PEF 활동 랭킹 저장 실패 (%s)", _OUTPUT_PATH)


def export_for_web(dest: Path) -> None:
    try:
        if not _OUTPUT_PATH.exists():
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(_OUTPUT_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        logger.exception("PEF 활동 랭킹 웹 내보내기 실패 (%s)", dest)
