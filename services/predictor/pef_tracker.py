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


def collect_pef_activity() -> list[dict]:
    end = dt.datetime.now(KST).date()
    start = end - dt.timedelta(days=_LOOKBACK_DAYS)
    bgn_de, end_de = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

    filings = list_recent_major_holder_filings(bgn_de, end_de)
    if not filings:
        return []

    # 회사 중복 제거 (같은 회사가 이 기간에 여러 번 공시했을 수 있음)
    companies = {f["corp_code"]: f for f in filings if f.get("corp_code")}
    logger.info("DART 대량보유상황보고서: %d개 회사에서 %d건 (최근 %d일)",
                len(companies), len(filings), _LOOKBACK_DAYS)

    rows: list[dict] = []
    for corp_code, meta in companies.items():
        history = fetch_major_holder_detail(corp_code)
        pef_net_buy = 0.0
        pef_reporters: set[str] = set()
        latest_report_reason = None
        latest_date = None

        for entry in history:
            rcept_dt = entry.get("rcept_dt", "")
            if not (bgn_de <= rcept_dt <= end_de):
                continue
            reporter = entry.get("repror", "")
            if not looks_like_pef(reporter):
                continue

            delta = _parse_number(entry.get("stkqy_irds"))
            pef_net_buy += delta
            pef_reporters.add(reporter)
            if latest_date is None or rcept_dt > latest_date:
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
