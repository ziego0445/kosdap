"""1차 신호: 토큰화 주식 / 무기한선물 가격 (24/7, 주말 포함).

- SKHYB/USDT: Binance 공개 REST API
- SMSN/USD: Hyperliquid 공개 API (무기한선물 mid price)

주의: 두 API 모두 심볼 표기/응답 필드가 거래소 업데이트로 바뀔 수 있으니
실제 연동 전에 각 거래소 공식 문서로 한 번 더 확인할 것.
"""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"
HYPERLIQUID_INFO_URL = "https://api.hyperliquid.xyz/info"


def fetch_binance_price(symbol: str = "SKHYBUSDT") -> float | None:
    """Binance 현물 티커 마지막 체결가."""
    try:
        resp = requests.get(BINANCE_TICKER_URL, params={"symbol": symbol}, timeout=10)
        resp.raise_for_status()
        return float(resp.json()["price"])
    except Exception:
        logger.exception("Binance price fetch failed for %s", symbol)
        return None


def fetch_hyperliquid_mid(coin: str = "SMSN") -> float | None:
    """Hyperliquid 무기한선물 mid price (allMids)."""
    try:
        resp = requests.post(
            HYPERLIQUID_INFO_URL,
            json={"type": "allMids"},
            timeout=10,
        )
        resp.raise_for_status()
        mids = resp.json()
        price = mids.get(coin)
        return float(price) if price is not None else None
    except Exception:
        logger.exception("Hyperliquid mid fetch failed for %s", coin)
        return None


def collect_token_prices() -> dict[str, float | None]:
    return {
        "SKHYNIX_token": fetch_binance_price("SKHYBUSDT"),
        "SAMSUNG_token": fetch_hyperliquid_mid("SMSN"),
    }
