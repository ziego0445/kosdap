"""KRX 장 운영 상태 판별 (KST 기준).

- open: 정규장 09:00~15:30 (평일) — 실시간 체결가 있음 -> 실제가 표시
- pre_market / post_market: 시간외 단일가 07:30~08:30 / 16:00~18:00 —
  2026-08-07부터 collectors.krx.fetch_after_hours_price()로 실제 체결가
  연동됨 (docs/PRD.md 3.4) -> 실제가 표시
- closed: 그 외(평일 야간, 토·일) — 실제가 없음 -> 추정가 표시

주의: 08:30~09:00(동시호가 접수)과 15:30~16:00(종가 확정/시간외종가매매)는
정규장도, 실제 "시간외 단일가"도 아닌 전환 구간이다. fetch_after_hours_price()
가 참조하는 네이버 overMarketPriceInfo.overPrice는 이 구간엔 실제 체결가가
아니라 예상체결가(개장가 근사치) 등 부정확한 값을 준다 — 실측 확인(2026-08-14,
08:55 스냅샷의 currentPrice가 실시간가가 아니라 당일 시가와 정확히 일치했음).
그래서 이 두 구간은 pre_market/post_market에 포함시키지 않고 closed(추정가)로
취급한다.
"""

from __future__ import annotations

import datetime as dt

KST = dt.timezone(dt.timedelta(hours=9))

REGULAR_OPEN = dt.time(9, 0)
REGULAR_CLOSE = dt.time(15, 30)
PRE_MARKET_START = dt.time(7, 30)
PRE_MARKET_END = dt.time(8, 30)
POST_MARKET_START = dt.time(16, 0)
POST_MARKET_END = dt.time(18, 0)


def get_session(now_kst: dt.datetime | None = None) -> str:
    now_kst = now_kst or dt.datetime.now(KST)
    if now_kst.weekday() >= 5:  # 토(5)/일(6)
        return "closed"

    t = now_kst.time()
    if REGULAR_OPEN <= t <= REGULAR_CLOSE:
        return "open"
    if PRE_MARKET_START <= t < PRE_MARKET_END:
        return "pre_market"
    if POST_MARKET_START <= t <= POST_MARKET_END:
        return "post_market"
    return "closed"


def has_real_price_feed(session: str) -> bool:
    """이 세션에 대해 '실제가' 소스가 이미 연동돼 있는지."""
    return session in ("open", "pre_market", "post_market")
