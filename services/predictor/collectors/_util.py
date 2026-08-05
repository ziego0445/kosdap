"""Shared helpers for yfinance-based collectors."""

from __future__ import annotations

import logging

import yfinance as yf

logger = logging.getLogger(__name__)


def pct_change(ticker: str) -> float | None:
    """전일 종가 대비 최근 종가 변동률(%)."""
    try:
        hist = yf.Ticker(ticker).history(period="2d", interval="1d")
        if len(hist) < 2:
            return None
        prev, last = hist["Close"].iloc[-2], hist["Close"].iloc[-1]
        return round(float((last - prev) / prev * 100), 3)
    except Exception:
        logger.exception("pct_change fetch failed for %s", ticker)
        return None
