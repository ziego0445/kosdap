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

추가(사용자 피드백, 2026-08-08): 하루짜리 스파이크는 노이즈(단발성
블록딜 등)일 수 있어서, "며칠 연속으로 매수가 들어왔는지"(연속 매수일)
도 같이 본다 — 이미 받아둔 250일 히스토리로 추가 API 호출 없이 계산
가능. 여러 날 연속 순매수가 하루짜리 스파이크보다 진짜 매집일 가능성이
높다고 보고, 정렬 기준도 연속일수를 1순위로 바꿨다.

추가(사용자 요청, 2026-08-08): 사모뿐 아니라 기관 자금도 같이 들어온
종목이 더 강한 신호라고 보고, "복합 수급 신호"(collect_combined_signal_
activity)를 추가했다. "같은 날 동시에" 조건은 두지 않는다 — 사모는
어제, 기관은 오늘처럼 날짜가 어긋나도 잡히도록, 두 카테고리 각각의
상위 후보를 합집합으로 모아 연속매수일을 독립적으로 계산하고 점수만
단순 합산한다(사용자 표현 그대로 "따로 보여주고 점수만 합산"). "매수
의견"처럼 여러 신호를 하나의 판단으로 바꿔치기하지는 않는다 — kosdap
전체 원칙(계산된 사실은 보여주되 판단은 안 함)에 따라 각 지표를 그대로
나란히 보여주고 정렬만 점수로 하는 데 그친다.

주의: KRX "기관합계"는 "사모"를 포함하는 상위 카테고리라, 그대로 같이
쓰면 같은 자금을 두 번 세는 꼴이 된다. 그래서 "기관(사모 제외)" =
금융투자+보험+투신+은행+기타금융+연기금(사모 제외 6개 하위분류 합)으로
따로 계산해서, 진짜 서로 다른 두 자금원이 같이 들어왔는지를 본다.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

import pandas as pd

from collectors.krx_flows import (
    fetch_daily_investor_detail_history,
    fetch_daily_net_buy_history,
    fetch_market_cap_by_ticker,
    fetch_today_net_buy_by_ticker,
)
from collectors.market_hours import KST

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent / "data"
_OUTPUT_PATH = _DATA_DIR / "pef_flow_activity.json"
_COMBINED_OUTPUT_PATH = _DATA_DIR / "pef_combined_signal.json"

_TOP_CANDIDATES = 120  # 오늘 순매수 절대금액 상위 몇 개까지 상세조회할지
_DISPLAY_LIMIT = 20  # 화면엔 정렬 후 상위 20개까지만 (사용자 요청, 2026-08-09)
_HISTORY_TRADING_DAYS_LABEL = 250  # UI 표기용("최근 1년" 근사)
_HISTORY_CALENDAR_BUFFER_DAYS = 380  # 주말/공휴일 감안 여유

# "기관합계"에서 "사모"를 뺀 순수 기관 자금 하위분류 (위 docstring 참고).
_INSTITUTION_EXCL_PEF_COLUMNS = ["금융투자", "보험", "투신", "은행", "기타금융", "연기금"]

_MARKET_LABELS = {"KOSPI": "코스피", "KOSDAQ": "코스닥"}


def _market_label(raw: str | None) -> str | None:
    if raw is None:
        return None
    return _MARKET_LABELS.get(raw, raw)


def _compute_rank(history: pd.Series, today_value: float) -> int:
    """오늘보다 절대금액이 더 강했던 과거 날짜 수 + 1 (1위=최근 1년 중
    가장 강한 날). 매도(음수)도 "강한 수급"이라 절대값으로 비교한다."""
    return int((history.abs() > abs(today_value)).sum()) + 1


def _compute_streak(history: pd.Series) -> tuple[int, float]:
    """오늘부터 거슬러가며 순매수(양수)가 끊기지 않고 이어진 (일수, 누적금액)."""
    days = 0
    total = 0.0
    for v in reversed(history.tolist()):
        if v <= 0:
            break
        days += 1
        total += v
    return days, total


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
        rank = _compute_rank(history, today_value)
        sample_days = len(history)
        consecutive_buy_days, streak_total_value = _compute_streak(history)

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
                "market": _market_label(row.get("시장")),
                "netBuyValueKrw": round(today_value),
                "rank": rank,
                "sampleDays": sample_days,
                "consecutiveBuyDays": consecutive_buy_days,
                "streakTotalValueKrw": round(streak_total_value),
                "marketCapKrw": round(market_cap) if market_cap else None,
                "netBuyPercentOfCap": pct_of_cap,
            }
        )

    # 며칠 연속으로 들어왔는지를 1순위로 본다(하루짜리 스파이크보다
    # 진짜 매집 가능성이 높다고 보고) — 동률이면 오늘 순위가 강한(1에
    # 가까운) 쪽, 그다음 시총 대비 비율이 큰 쪽을 우선.
    rows.sort(
        key=lambda r: (
            -r["consecutiveBuyDays"],
            r["rank"],
            -(r["netBuyPercentOfCap"] or 0),
        )
    )
    return {"tradeDate": _to_dashed(date_str), "rows": rows[:_DISPLAY_LIMIT]}


def collect_combined_signal_activity() -> dict:
    """사모 + 기관(사모 제외)이 같은 날 같은 방향(순매수)으로 들어온
    종목만 골라, 각자의 연속매수일/금액을 나란히 보여준다.

    사용자 피드백(2026-08-28)으로 "같은 날 동시에 들어온 것만"에서
    "각자 따로 계산해서 점수만 합산"으로 바꿈 — 사모는 어제, 기관은
    오늘 들어온 것처럼 날짜가 어긋나도 잡히도록, 두 카테고리의 상위
    후보를 합집합으로 모아서 각자의 연속매수일을 독립적으로 계산하고
    점수만 더한다(교집합 조건 없음)."""
    date_str, pef_today = _find_latest_trading_date()
    if date_str is None or pef_today is None or pef_today.empty:
        logger.warning("복합 수급 신호: 사모 데이터 조회 실패")
        return {"tradeDate": None, "rows": []}

    inst_today = fetch_today_net_buy_by_ticker(date_str, investor="기관합계")
    if inst_today.empty:
        logger.warning("복합 수급 신호: 기관합계 데이터 조회 실패")
        return {"tradeDate": _to_dashed(date_str), "rows": []}

    # 두 카테고리 각각 "오늘 순매수 상위" 후보를 뽑고 합집합으로 모은다
    # (교집합이 아님 — 한쪽만 오늘 강해도 후보에 들어감).
    pef_buys = pef_today[pef_today["순매수거래대금"] > 0]
    pef_candidates = pef_buys.reindex(
        pef_buys["순매수거래대금"].sort_values(ascending=False).index
    ).head(_TOP_CANDIDATES)

    inst_buys = inst_today[inst_today["순매수거래대금"] > 0]
    inst_candidates = inst_buys.reindex(
        inst_buys["순매수거래대금"].sort_values(ascending=False).index
    ).head(_TOP_CANDIDATES)

    info_by_ticker = {}
    for df in (pef_candidates, inst_candidates):
        for ticker, row in df.iterrows():
            info_by_ticker.setdefault(
                ticker, {"name": row.get("종목명"), "market": row.get("시장")}
            )

    if not info_by_ticker:
        return {"tradeDate": _to_dashed(date_str), "rows": []}

    end_date = dt.datetime.strptime(date_str, "%Y%m%d").date()
    start_date = end_date - dt.timedelta(days=_HISTORY_CALENDAR_BUFFER_DAYS)
    start_str, end_str = start_date.strftime("%Y%m%d"), end_date.strftime("%Y%m%d")

    rows: list[dict] = []
    for ticker, info in info_by_ticker.items():
        detail = fetch_daily_investor_detail_history(ticker, start_str, end_str)
        if detail is None or detail.empty or "사모" not in detail.columns:
            continue
        inst_cols = [c for c in _INSTITUTION_EXCL_PEF_COLUMNS if c in detail.columns]
        if not inst_cols:
            continue

        pef_series = detail["사모"]
        inst_series = detail[inst_cols].sum(axis=1)  # "기관합계 - 사모" (이중계산 방지)

        pef_today_value = float(pef_series.iloc[-1])
        inst_today_value = float(inst_series.iloc[-1])

        # 각자 독립적으로 계산 — 오늘 이 카테고리가 매도/보합이어도(연속
        # 매수일=0이 될 뿐) 다른 카테고리 점수가 있으면 후보로 남는다.
        pef_days, pef_streak_total = _compute_streak(pef_series)
        inst_days, inst_streak_total = _compute_streak(inst_series)

        if pef_days == 0 and inst_days == 0:
            continue  # 둘 다 오늘 매수가 아니면(연속 0) 신호랄 게 없음

        pef_rank = _compute_rank(pef_series, pef_today_value) if pef_today_value > 0 else None
        inst_rank = _compute_rank(inst_series, inst_today_value) if inst_today_value > 0 else None

        rows.append(
            {
                "ticker": ticker,
                "corpName": info["name"],
                "market": _market_label(info["market"]),
                "pefNetBuyValueKrw": round(pef_today_value),
                "pefConsecutiveBuyDays": pef_days,
                "pefStreakTotalValueKrw": round(pef_streak_total),
                "pefRank": pef_rank,
                "institutionNetBuyValueKrw": round(inst_today_value),
                "institutionConsecutiveBuyDays": inst_days,
                "institutionStreakTotalValueKrw": round(inst_streak_total),
                "institutionRank": inst_rank,
                "combinedScore": pef_days + inst_days,
                "sampleDays": len(pef_series),
            }
        )

    # 점수(사모 연속일수 + 기관 연속일수 단순 합산)가 높은 순 — "따로 보여
    # 주고 점수만 합산"(사용자 요청 문구 그대로).
    rows.sort(key=lambda r: -r["combinedScore"])
    return {"tradeDate": _to_dashed(date_str), "rows": rows[:_DISPLAY_LIMIT]}


def export_combined_signal_activity() -> None:
    result = collect_combined_signal_activity()
    try:
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        _COMBINED_OUTPUT_PATH.write_text(
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
            "복합 수급 신호 저장: %s (%d개 종목)",
            _COMBINED_OUTPUT_PATH, len(result["rows"]),
        )
    except Exception:
        logger.exception("복합 수급 신호 저장 실패 (%s)", _COMBINED_OUTPUT_PATH)


def export_combined_signal_for_web(dest: Path) -> None:
    try:
        if not _COMBINED_OUTPUT_PATH.exists():
            return
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(_COMBINED_OUTPUT_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        logger.exception("복합 수급 신호 웹 내보내기 실패 (%s)", dest)


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
