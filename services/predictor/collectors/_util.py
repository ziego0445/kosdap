"""Shared helpers for yfinance-based collectors."""

from __future__ import annotations

import logging

import yfinance as yf

logger = logging.getLogger(__name__)


def pct_change(ticker: str) -> float | None:
    """직전 종가 대비 최근 종가 변동률(%).

    당일 세션이 진행 중이면 최신 row의 OHLC가 NaN으로 채워질 수 있어 (실측
    확인됨) period="5d"로 넉넉히 받아 NaN을 제거한 뒤 마지막 두 값을 쓴다.
    """
    try:
        hist = yf.Ticker(ticker).history(period="5d", interval="1d")
        closes = hist["Close"].dropna()
        if len(closes) < 2:
            return None
        prev, last = closes.iloc[-2], closes.iloc[-1]
        return round(float((last - prev) / prev * 100), 3)
    except Exception:
        logger.exception("pct_change fetch failed for %s", ticker)
        return None
