"""1차 신호: 토큰화 주식/무기한선물 가격 (24/7, 주말 포함).

실측 결과 Bybit 무기한선물(linear perpetual)이 삼성전자·SK하이닉스 둘 다
하나의 API로 안정적으로 제공한다:
  - SAMSUNGUSDT (삼성전자, 실측 lastPrice ~175 USDT, volume24h ~40k)
  - SKHYNIXUSDT (SK하이닉스, 실측 lastPrice ~1176 USDT, volume24h ~80k)

Binance(SKHYB/USDT)도 SK하이닉스는 잡히지만 삼성전자는 상장이 안 되어 있고,
Hyperliquid 기본 perp universe에는 둘 다 없었다(2026-08-06 확인). 그래서
Bybit을 1순위로 쓰고, Binance SKHYB는 SK하이닉스 교차검증용 보조 소스로 남긴다.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import requests

logger = logging.getLogger(__name__)

BYBIT_TICKERS_URL = "https://api.bybit.com/v5/market/tickers"
BYBIT_KLINE_URL = "https://api.bybit.com/v5/market/kline"
BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/price"

BYBIT_SYMBOLS = {
    "SAMSUNG": "SAMSUNGUSDT",
    "SKHYNIX": "SKHYNIXUSDT",
}


def fetch_bybit_price(symbol: str) -> float | None:
    try:
        resp = requests.get(
            BYBIT_TICKERS_URL,
            params={"category": "linear", "symbol": symbol},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        rows = data.get("result", {}).get("list", [])
        if not rows:
            return None
        return float(rows[0]["lastPrice"])
    except Exception:
        logger.exception("Bybit price fetch failed for %s", symbol)
        return None


KRX_CLOSE_HOUR_UTC = 6  # KST 15:30 장마감 ≈ UTC 06:30 (근사치, 조기폐장/휴장일 미반영)
KRX_CLOSE_MINUTE_UTC = 30


def fetch_bybit_daily_close(symbol: str, trade_date: str) -> float | None:
    """호환용 래퍼. fetch_bybit_close_at_krx_close를 쓸 것 — 아래 설명 참고."""
    return fetch_bybit_close_at_krx_close(symbol, trade_date)


def fetch_bybit_close_at_krx_close(symbol: str, trade_date: str) -> float | None:
    """`trade_date`("YYYY-MM-DD")의 KRX 장마감 시각(KST 15:30 ≈ UTC 06:30)에
    가장 가까운 Bybit 시간봉 종가.

    token_change_percent 계산의 기준가(basis)로 쓴다: 토큰가(USDT)와 KRX
    종가(KRW)는 통화가 달라 직접 비교할 수 없으므로, "KRX 마감 시점의 토큰
    가격" 대비 "현재 토큰가"의 변동률(같은 통화, USDT/USDT)을 구해서 그
    비율을 KRW 종가에 곱하는 방식으로 우회한다.

    실측으로 발견한 버그: 처음엔 일봉(UTC 00:00~24:00 단위)을 썼는데, KRX
    마감(UTC 06:30)이 그 UTC 일봉 구간의 초반부라 "그날 일봉 종가"는 실제로
    다음날 KST 08:59까지의 가격을 반영해버림 — 조회 시점이 마침 그 근처면
    기준가와 현재가가 사실상 같아져서 token_change가 0에 수렴하는 문제가
    있었다. 시간봉으로 마감 시각에 정확히 맞춰서 해결.
    """
    try:
        target = datetime.strptime(trade_date, "%Y-%m-%d").replace(
            hour=KRX_CLOSE_HOUR_UTC, minute=KRX_CLOSE_MINUTE_UTC, tzinfo=UTC
        )
        resp = requests.get(
            BYBIT_KLINE_URL,
            params={
                "category": "linear",
                "symbol": symbol,
                "interval": "60",
                "end": int(target.timestamp() * 1000),
                "limit": 3,
            },
            timeout=10,
        )
        resp.raise_for_status()
        rows = resp.json().get("result", {}).get("list", [])
        if not rows:
            return None
        return float(rows[0][4])  # 가장 최근(=target 이하 중 최신) 캔들의 종가
    except Exception:
        logger.exception("Bybit hourly close fetch failed for %s @ %s", symbol, trade_date)
        return None


def fetch_binance_price(symbol: str = "SKHYBUSDT") -> float | None:
    """보조 교차검증 소스 (SK하이닉스만 상장돼 있음)."""
    try:
        resp = requests.get(BINANCE_TICKER_URL, params={"symbol": symbol}, timeout=10)
        resp.raise_for_status()
        return float(resp.json()["price"])
    except Exception:
        logger.exception("Binance price fetch failed for %s", symbol)
        return None


def collect_token_prices() -> dict[str, float | None]:
    return {
        f"{symbol}_token": fetch_bybit_price(bybit_symbol)
        for symbol, bybit_symbol in BYBIT_SYMBOLS.items()
    }
