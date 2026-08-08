"""사모펀드 수급 이례치 탐지 — KRX 투자자별 매매동향 기반.

DART 5%룰 공시 기반 pef_tracker.py와는 접근이 다르다:
- pef_tracker.py: 개별 펀드명이 나오지만(예: "루하프라이빗에쿼티") 5% 이상
  지분공시가 실제로 발생한 종목만 커버.
- 이 모듈: KRX 공식 투자자 분류 "사모"(경영참여형 PEF + 헤지펀드성 사모펀드
  합산 카테고리) 데이터로 전종목을 커버하지만, 집계치라 개별 펀드명은
  알 수 없다.

방법론(사용자 요청, 2026-08-08 — Pluto Research라는 서비스가 쓰는 방식을
참고): 오늘 "사모" 순매수 절대금액이, 그 종목 자체의 최근 250거래일
역사 중 몇 번째로 강했는지 순위를 매긴다(종목 간 비교가 아니라 "그
종목 스스로의 평소 대비 이례적인 정도"). 전종목(코스피+코스닥, 2천개
이상)을 다 이렇게 조회하면 종목당 왕복 시간 때문에 20~30분이 걸려
비현실적이라(실측 확인), 먼저 "오늘 순매수 절대금액" 상위 후보만 추린
뒤 그 후보들만 250일 히스토리를 조회한다.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

from collectors.krx_flows import (
    fetch_daily_net_buy_history,
    fetch_market_cap_by_ticker,
    fetch_today_net_buy_by_ticker,
)
from collectors.market_hours import KST

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent / "data"
_OUTPUT_PATH = _DATA_DIR / "pef_flow_activity.json"

_TOP_CANDIDATES = 120  # 오늘 순매수 절대금액 상위 몇 개까지 상세조회할지
_HISTORY_TRADING_DAYS_LABEL = 250  # UI 표기용("최근 1년" 근사)
_HISTORY_CALENDAR_BUFFER_DAYS = 380  # 주말/공휴일 감안 여유


def _find_latest_trading_date():
    """오늘부터 최대 7일 거슬러가며 데이터가 있는 가장 최근 거래일을 찾는다
    (주말/공휴일엔 당연히 빈 응답이 오므로)."""
    today = dt.datetime.now(KST).date()
    for delta in range(0, 8):
        d = today - dt.timedelta(days=delta)
        date_str = d.strftime("%Y%m%d")
        df = fetch_today_net_buy_by_ticker(date_str)
        if not df.empty:
            return date_str, df
    return None, None


def collect_pef_flow_activity() -> dict:
    date_str, today_df = _find_latest_trading_date()
    if date_str is None or today_df is None or today_df.empty:
        logger.warning("사모 수급 데이터 조회 실패 — 최근 7일 모두 빈 응답")
        return {"tradeDate": None, "rows": []}

    # 매수(양수)만 본다 — "뭐샀니" 탭이라 매도는 범위 밖.
    buys = today_df[today_df["순매수거래대금"] > 0]
    if buys.empty:
        return {"tradeDate": _to_dashed(date_str), "rows": []}
    candidates = buys.reindex(
        buys["순매수거래대금"].sort_values(ascending=False).index
    ).head(_TOP_CANDIDATES)

    cap_df = fetch_market_cap_by_ticker(date_str)

    end_date = dt.datetime.strptime(date_str, "%Y%m%d").date()
    start_date = end_date - dt.timedelta(days=_HISTORY_CALENDAR_BUFFER_DAYS)
    start_str, end_str = start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")

    rows: list[dict] = []
    for ticker, row in candidates.iterrows():
        history = fetch_daily_net_buy_history(ticker, start_str, end_str)
        if history is None or history.empty:
            continue
        today_value = float(history.iloc[-1])
        if today_value <= 0:
            continue
        # 순위: 오늘보다 절대금액이 더 강했던 과거 날짜 수 + 1 (1위=최근
        # 1년 중 가장 강한 날). 매도(음수)도 "강한 수급"이라 절대값 비교.
        rank = int((history.abs() > abs(today_value)).sum()) + 1
        sample_days = len(history)

        market_cap = None
        pct_of_cap = None
        if ticker in cap_df.index:
            market_cap = float(cap_df.loc[ticker, "시가총액"])
            if market_cap:
                pct_of_cap = round(today_value / market_cap * 100, 3)

        rows.append(
            {
                "ticker": ticker,
                "corpName": row.get("종목명"),
                "netBuyValueKrw": round(today_value),
                "rank": rank,
                "sampleDays": sample_days,
                "marketCapKrw": round(market_cap) if market_cap else None,
                "netBuyPercentOfCap": pct_of_cap,
            }
        )

    # 순위가 1에 가까울수록("최근 1년 중 가장 강했던 날") 강한 신호.
    # 동률이면 시총 대비 비율이 큰 쪽을 우선.
    rows.sort(key=lambda r: (r["rank"], -(r["netBuyPercentOfCap"] or 0)))
    return {"tradeDate": _to_dashed(date_str), "rows": rows}


def _to_dashed(yyyymmdd: str) -> str:
    return f"{yyyymmdd[:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"


def export_pef_flow_activity() -> None:
    result = collect_pef_flow_activity()
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _OUTPUT_PATH.write_text(
            json.dumps(
                {
                    "generatedAt": dt.datetime.now(dt.UTC).isoformat(),
                    "tradeDate": result["tradeDate"],
                    "historyTradingDaysApprox": _HISTORY_TRADING_DAYS_LABEL,
                    "rows": result["rows"],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        logger.info(
            "사모 수급 이례치 저장: %s (%d개 종목)", _OUTPUT_PATH, len(result["rows"])
        )
    except Exception:
        logger.exception("사모 수급 이례치 저장 실패 (%s)", _OUTPUT_PATH)


def export_for_web(dest: Path) -> None:
    try:
        if not _OUTPUT_PATH.exists():
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(_OUTPUT_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        logger.exception("사모 수급 이례치 웹 내보내기 실패 (%s)", dest)
