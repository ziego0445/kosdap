"""KRX 종가 및 시간외 데이터.

fetch_last_close()는 yfinance(005930.KS 등)로 실제 종가를 가져온다 — 정식
공급자는 아니라 지연/오류 가능성이 있으니 운영 단계에서는 증권사 API로 교체
검토할 것.

fetch_after_hours_price()는 '추정'이 필요 없는 실제 시간외 체결 구간
(16:00~18:00, 07:30~08:30) 데이터로, 아직 소스가 정해지지 않은 스텁이다
(docs/PRD.md 3.4 참고).
"""

from __future__ import annotations

import datetime as dt
import logging

import yfinance as yf

logger = logging.getLogger(__name__)


def fetch_last_close(krx_ticker: str) -> float | None:
    price, _ = fetch_last_close_with_date(krx_ticker)
    return price


def fetch_last_close_with_date(krx_ticker: str) -> tuple[float | None, str | None]:
    """(종가, 거래일자 'YYYY-MM-DD') 튜플을 반환한다.

    날짜가 필요한 이유: 토큰가(USDT)와 KRX 종가(KRW)는 통화 단위가 달라 직접
    뺄셈하면 안 되고, "같은 날짜의 토큰 종가 대비 현재 토큰가 변동률"을 KRW
    종가에 적용해야 한다 (collectors/tokenized.fetch_bybit_daily_close 참고).
    """
    try:
        hist = yf.Ticker(krx_ticker).history(period="5d", interval="1d")
        closes = hist["Close"].dropna()
        # 당일 세션이 아직 진행 중이면 마지막 row가 NaN으로 채워져 있을 수 있음
        # (실측 확인됨: 장중에 fetch하면 today row의 OHLC가 전부 NaN) — 값이
        # 있는 가장 최근 row를 써야 한다.
        if closes.empty:
            return None, None
        last_date = closes.index[-1].strftime("%Y-%m-%d")
        return float(closes.iloc[-1]), last_date
    except Exception:
        logger.exception("KRX last close fetch failed for %s", krx_ticker)
        return None, None


def fetch_after_hours_price(krx_ticker: str) -> float | None:
    logger.warning(
        "fetch_after_hours_price(%s) is a stub — wire up KRX 시간외 데이터 소스",
        krx_ticker,
    )
    return None


def fetch_intraday_price(krx_ticker: str) -> float | None:
    """정규장(09:00~15:30 KST) 운영 중 실시간(근사) 체결가.

    yfinance의 1분봉 중 가장 최근 값을 쓴다 — 몇 분 지연될 수 있으나 실제
    체결가 기반이라 "추정"이 아니다. 장이 열려있을 때만 의미있는 값을 준다.
    실측 확인: 장중에는 일봉(1d)의 Close도 이미 실시간에 가깝게 갱신되고
    있었음 — 다만 "오늘 대비 등락률" 계산엔 전일 완결 종가가 따로 필요해서
    fetch_previous_close()를 별도로 둔다.
    """
    try:
        hist = yf.Ticker(krx_ticker).history(period="1d", interval="1m")
        closes = hist["Close"].dropna()
        if closes.empty:
            return None
        return float(closes.iloc[-1])
    except Exception:
        logger.exception("KRX intraday price fetch failed for %s", krx_ticker)
        return None


def fetch_previous_close(krx_ticker: str) -> tuple[float | None, str | None]:
    """오늘(KST)을 제외한, 가장 최근 완결 거래일의 종가.

    장중엔 fetch_last_close_with_date가 "오늘의 실시간 값"을 돌려주므로
    (일봉 Close가 장중에도 계속 갱신됨을 실측 확인), 오늘 대비 등락률을
    구하려면 어제(혹은 그 이전) 완결 종가가 따로 필요하다.
    """
    try:
        hist = yf.Ticker(krx_ticker).history(period="10d", interval="1d")
        closes = hist["Close"].dropna()
        if closes.empty:
            return None, None
        today_kst = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
        prior = closes[closes.index.date != today_kst]
        if prior.empty:
            return None, None
        return float(prior.iloc[-1]), prior.index[-1].strftime("%Y-%m-%d")
    except Exception:
        logger.exception("KRX previous close fetch failed for %s", krx_ticker)
        return None, None
