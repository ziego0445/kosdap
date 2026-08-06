"""KRX 장 운영 상태 판별 (KST 기준).

- open: 정규장 09:00~15:30 (평일) — 실시간 체결가 있음 -> 실제가 표시
- pre_market / post_market: 시간외 단일가 07:30~08:30 / 16:00~18:00 —
  원래는 실제 체결가가 있어야 하지만 fetch_after_hours_price가 아직 스텁이라
  (docs/PRD.md 3.4) 현재는 closed와 동일하게 추정치로 취급한다. TODO: 실제
  소스 연동되면 여기서 분기해서 실제가로 전환.
- closed: 그 외(평일 야간, 토·일) — 실제가 없음 -> 추정가 표시
"""

from __future__ import annotations

import datetime as dt

KST = dt.timezone(dt.timedelta(hours=9))

REGULAR_OPEN = dt.time(9, 0)
REGULAR_CLOSE = dt.time(15, 30)
PRE_MARKET_START = dt.time(7, 30)
POST_MARKET_END = dt.time(18, 0)


def get_session(now_kst: dt.datetime | None = None) -> str:
    now_kst = now_kst or dt.datetime.now(KST)
    if now_kst.weekday() >= 5:  # 토(5)/일(6)
        return "closed"

    t = now_kst.time()
    if REGULAR_OPEN <= t <= REGULAR_CLOSE:
        return "open"
    if PRE_MARKET_START <= t < REGULAR_OPEN:
        return "pre_market"
    if REGULAR_CLOSE < t <= POST_MARKET_END:
        return "post_market"
    return "closed"


def has_real_price_feed(session: str) -> bool:
    """이 세션에 대해 '실제가' 소스가 이미 연동돼 있는지. pre_market/post_market은
    이론적으로 실제가가 있어야 하지만 아직 스텁이라 False.
    """
    return session == "open"
