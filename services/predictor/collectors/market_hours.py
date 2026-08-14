"""KRX 장 운영 상태 판별 (KST 기준).

- open: 정규장 09:00~15:30 (평일) — 실시간 체결가 있음 -> 실제가 표시
- pre_market / post_market: 시간외 단일가 07:30~08:30 / 16:00~18:00 —
  2026-08-07부터 collectors.krx.fetch_after_hours_price()로 실제 체결가
  연동됨 (docs/PRD.md 3.4) -> 실제가 표시
- closed: 그 외(평일 야간, 토·일, 평일 중 KRX 공휴일) — 실제가 없음 -> 추정가 표시

주의(공휴일): 요일만으론 설날/추석/광복절처럼 평일에 걸리는 공휴일을 못
거른다 — 실측으로 발견(2026-08-17 광복절 대체공휴일이 월요일). holidays
라이브러리(오프라인 계산, 매 세션 판정마다 불러도 네트워크 비용 없음)로
평일 공휴일도 closed 처리한다. 다만 이건 근사치다: 정부가 그때그때
지정하는 임시공휴일(예: 선거일)은 라이브러리가 미리 알 수 없어 못 잡고,
설/추석 연휴 전날 조기폐장 같은 "단축거래"도 별도 처리하지 않는다(그날은
여전히 open으로 판정되고, 실제 폐장 이후엔 그냥 fetch_intraday_price가
같은 값을 반복해서 줄 뿐 — 표시가 틀리진 않고 갱신이 좀 늦게 멈추는 정도).

주의(전환 구간): 08:30~09:00(동시호가 접수)과 15:30~16:00(종가 확정/시간외종가매매)는
정규장도, 실제 "시간외 단일가"도 아닌 전환 구간이다. fetch_after_hours_price()
가 참조하는 네이버 overMarketPriceInfo.overPrice는 이 구간엔 실제 체결가가
아니라 예상체결가(개장가 근사치) 등 부정확한 값을 준다 — 실측 확인(2026-08-14,
08:55 스냅샷의 currentPrice가 실시간가가 아니라 당일 시가와 정확히 일치했음).
그래서 이 두 구간은 pre_market/post_market에 포함시키지 않고 closed(추정가)로
취급한다.
"""

from __future__ import annotations

import datetime as dt
from functools import lru_cache

import holidays

KST = dt.timezone(dt.timedelta(hours=9))

REGULAR_OPEN = dt.time(9, 0)
REGULAR_CLOSE = dt.time(15, 30)
PRE_MARKET_START = dt.time(7, 30)
PRE_MARKET_END = dt.time(8, 30)
POST_MARKET_START = dt.time(16, 0)
POST_MARKET_END = dt.time(18, 0)


@lru_cache(maxsize=8)
def _kr_holidays(year: int) -> holidays.HolidayBase:
    """연도별 한국 공휴일 집합 (대체공휴일 포함). 오프라인 계산이라 네트워크
    비용 없이 캐싱해두고 재사용 — get_session()이 스케줄러 tick마다 불림."""
    return holidays.KR(years=[year])


def is_krx_holiday(d: dt.date) -> bool:
    """평일인데 한국 공휴일이라 KRX가 쉬는 날인지. 근사치임 — 클래스
    docstring의 "주의(공휴일)" 참고."""
    return d in _kr_holidays(d.year)


def get_session(now_kst: dt.datetime | None = None) -> str:
    now_kst = now_kst or dt.datetime.now(KST)
    if now_kst.weekday() >= 5:  # 토(5)/일(6)
        return "closed"
    if is_krx_holiday(now_kst.date()):
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
