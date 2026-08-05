"""3차 신호: 공매도비율, 외국인/기관 순매수 — 하루 1회, 장마감 후 갱신.

TODO: 실제 소스 확정 필요 (KRX 정보데이터시스템 공식 API 또는 네이버페이 증권
스크래핑). 현재는 인터페이스만 정의된 스텁이며, 매 실행마다 동일 값을 반환하지
않도록 스케줄러에서 하루 1회만 호출한다 (config.INTERVAL_FLOWS_SECONDS).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def collect_daily_flows(krx_ticker: str) -> dict[str, float | None]:
    logger.warning(
        "collect_daily_flows(%s) is a stub — wire up KRX/네이버 데이터 소스",
        krx_ticker,
    )
    return {
        "short_selling_ratio": None,
        "foreign_net_buy": None,
        "institution_net_buy": None,
    }
