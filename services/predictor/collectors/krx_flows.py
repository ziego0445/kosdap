"""KRX 투자자별(사모 등) 종목별 매매동향 — pykrx 래퍼.

data.krx.co.kr 로그인 세션이 필요하다 (공매도비율과 동일한 이유,
collectors/flows.py의 pykrx 사용부 참고 — 실측 확인: 로그인 없이는 빈
응답). pef_flow_tracker.py가 "오늘 사모 수급이 이 종목 자체의 최근 1년
역사 중 얼마나 이례적인지" 순위를 매길 때 쓴다.
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)

MARKETS = ["KOSPI", "KOSDAQ"]


def fetch_today_net_buy_by_ticker(date_str: str, investor: str = "사모") -> pd.DataFrame:
    """`date_str`(YYYYMMDD) 하루치, 전종목(코스피+코스닥) 투자자 카테고리별
    순매수거래대금. 반환 인덱스: 티커(6자리), 컬럼엔 종목명/순매수거래대금 등."""
    from pykrx import stock

    frames = []
    for market in MARKETS:
        try:
            df = stock.get_market_trading_value_and_volume_by_ticker(
                date_str, date_str, market, investor=investor
            )
            if not df.empty:
                frames.append(df)
        except Exception:
            logger.exception("%s %s 전종목 수급 조회 실패", market, date_str)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames)


def fetch_market_cap_by_ticker(date_str: str) -> pd.DataFrame:
    """`date_str` 하루치 전종목 시가총액. 인덱스: 티커."""
    from pykrx import stock

    frames = []
    for market in MARKETS:
        try:
            df = stock.get_market_cap_by_ticker(date_str, market=market)
            if not df.empty:
                frames.append(df)
        except Exception:
            logger.exception("%s %s 시가총액 조회 실패", market, date_str)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames)


def fetch_daily_net_buy_history(
    ticker: str, start_date: str, end_date: str, investor_column: str = "사모"
) -> pd.Series | None:
    """`ticker` 하나의 [start_date, end_date] 일별 `investor_column`
    순매수거래대금 시계열 (detail=True라 사모/외국인/개인 등 세부
    카테고리로 나뉘어 나온다)."""
    from pykrx import stock

    try:
        df = stock.get_market_trading_value_by_date(
            start_date, end_date, ticker, detail=True
        )
        if investor_column not in df.columns:
            return None
        return df[investor_column]
    except Exception:
        logger.exception("%s 일별 수급 히스토리 조회 실패", ticker)
        return None
