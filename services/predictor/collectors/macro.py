"""매크로 팩터: USD/KRW, DXY, 미국10년물, VIX, BTC/ETH (보조 리스크 센티먼트)."""

from __future__ import annotations

from config import MACRO_PROXIES

from ._util import pct_change


def collect_macro_changes() -> dict[str, float | None]:
    return {ticker: pct_change(ticker) for ticker in MACRO_PROXIES}
