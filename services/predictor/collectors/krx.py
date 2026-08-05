"""KRX 종가 및 시간외 데이터.

fetch_last_close()는 yfinance(005930.KS 등)로 실제 종가를 가져온다 — 정식
공급자는 아니라 지연/오류 가능성이 있으니 운영 단계에서는 증권사 API로 교체
검토할 것.

fetch_after_hours_price()는 '추정'이 필요 없는 실제 시간외 체결 구간
(16:00~18:00, 07:30~08:30) 데이터로, 아직 소스가 정해지지 않은 스텁이다
(docs/PRD.md 3.4 참고).
"""

from __future__ import annotations

import logging

import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_last_close(krx_ticker: str) -> float | None:
    try:
        hist = yf.Ticker(krx_ticker).history(period="5d", interval="1d")
        if hist.empty:
            return None
        return float(hist["Close"].iloc[-1])
    except Exception:
        logger.exception("KRX last close fetch failed for %s", krx_ticker)
        return None


def fetch_after_hours_price(krx_ticker: str) -> float | None:
    logger.warning(
        "fetch_after_hours_price(%s) is a stub — wire up KRX 시간외 데이터 소스",
        krx_ticker,
    )
    return None
