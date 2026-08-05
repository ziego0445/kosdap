"""2차 신호: 해외 상관 종목 (Micron, Nvidia, SOXX, TSM 등) — 미국 정규장 시간대 위주.

yfinance는 비공식 스크래핑 기반 라이브러리라 장애 시 재시도/폴백이 필요할 수 있음.
"""

from __future__ import annotations

from config import EQUITY_PROXIES

from ._util import pct_change


def collect_equity_changes() -> dict[str, float | None]:
    """각 프록시 종목의 최근 종가 대비 변동률(%)."""
    return {ticker: pct_change(ticker) for ticker in EQUITY_PROXIES}
