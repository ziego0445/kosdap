"""KRX 종가 및 시간외 데이터.

fetch_last_close()는 yfinance(005930.KS 등)로 실제 종가를 가져온다 — 정식
공급자는 아니라 지연/오류 가능성이 있으니 운영 단계에서는 증권사 API로 교체
검토할 것.

fetch_after_hours_price()는 '추정'이 필요 없는 실제 시간외 체결 구간
(16:00~18:00, 07:30~08:30) 데이터. 2026-08-07 실측으로 네이버 금융
모바일이 쓰는 polling API에서 정확한 값을 찾아 연결함 (docs/PRD.md 3.4).
"""

from __future__ import annotations

import datetime as dt
import logging

import requests
import yfinance as yf

from .market_hours import KST

logger = logging.getLogger(__name__)

_NAVER_POLLING_URL = "https://polling.finance.naver.com/api/realtime/domestic/stock/{code}"
_MOBILE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)"


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


def _fetch_naver_price(krx_ticker: str, field_extractor) -> float | None:
    """네이버 금융 모바일 실시간 polling API 공통 호출부. `field_extractor`가
    응답의 첫 row에서 원하는 가격 필드를 뽑아 문자열("1,234,000")을 float로
    변환한다. 비공식 API라 응답 구조가 바뀌면 깨질 수 있음."""
    code = krx_ticker.split(".")[0]
    try:
        resp = requests.get(
            _NAVER_POLLING_URL.format(code=code),
            headers={"User-Agent": _MOBILE_UA},
            timeout=10,
        )
        resp.raise_for_status()
        rows = resp.json().get("datas", [])
        if not rows:
            return None
        raw = field_extractor(rows[0])
        if not raw:
            return None
        return float(str(raw).replace(",", ""))
    except Exception:
        logger.exception("Naver polling API fetch failed for %s", krx_ticker)
        return None


def fetch_after_hours_price(krx_ticker: str) -> float | None:
    """장전/장후 시간외 단일가(07:30~08:30, 16:00~18:00 KST) 실제 체결가.

    실측 확인(2026-08-07): 네이버 금융 모바일이 쓰는 실시간 polling API의
    `overMarketPriceInfo.overPrice` 필드가 정확히 이 값을 준다 (삼성전자·
    SK하이닉스 둘 다 확인함).
    """
    return _fetch_naver_price(
        krx_ticker,
        lambda row: (row.get("overMarketPriceInfo") or {}).get("overPrice"),
    )


def fetch_intraday_price_naver(krx_ticker: str) -> float | None:
    """정규장 중 네이버 실시간가(`closePrice` 필드 — 이름과 달리 장중엔
    "지금까지의 최신 체결가"를 계속 갱신해서 준다, 실측 확인 2026-08-18)."""
    return _fetch_naver_price(krx_ticker, lambda row: row.get("closePrice"))


def fetch_intraday_price(krx_ticker: str) -> float | None:
    """정규장(09:00~15:30 KST) 운영 중 실시간(근사) 체결가.

    1순위로 yfinance 1분봉 중 가장 최근 값을 쓴다 — 몇 분 지연될 수 있으나
    실제 체결가 기반이라 "추정"이 아니다. 실측 확인: 장중에는 일봉(1d)의
    Close도 이미 실시간에 가깝게 갱신되고 있었음 — 다만 "오늘 대비 등락률"
    계산엔 전일 완결 종가가 따로 필요해서 fetch_previous_close()를 별도로 둔다.

    2026-08-18 실측: yfinance가 특정 종목(SK하이닉스)만 당일 1분봉/일봉을
    통째로 못 주는 경우가 있었음(다른 종목은 정상 — Yahoo 쪽 종목별 데이터
    지연/장애로 추정, 우리 쪽 원인 아님). 네이버 실시간가(이미
    fetch_after_hours_price가 신뢰하는 같은 소스)로 폴백해서 이런 날에도
    끊기지 않게 한다.
    """
    try:
        hist = yf.Ticker(krx_ticker).history(period="1d", interval="1m")
        closes = hist["Close"].dropna()
        if not closes.empty:
            return float(closes.iloc[-1])
    except Exception:
        logger.exception("KRX intraday price fetch failed for %s (yfinance)", krx_ticker)

    logger.warning("%s: yfinance 1분봉 조회 실패/빈 응답 — 네이버 실시간가로 폴백", krx_ticker)
    return fetch_intraday_price_naver(krx_ticker)


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
        today_kst = dt.datetime.now(KST).date()
        prior = closes[closes.index.date != today_kst]
        if prior.empty:
            return None, None
        return float(prior.iloc[-1]), prior.index[-1].strftime("%Y-%m-%d")
    except Exception:
        logger.exception("KRX previous close fetch failed for %s", krx_ticker)
        return None, None


def fetch_close_price_on_or_before(krx_ticker: str, date_str: str) -> float | None:
    """`date_str`("YYYY-MM-DD") 당일 또는 그 직전 가장 가까운 거래일 종가.

    PEF 지분공시(pef_tracker.py)에서 "매수 규모가 대략 얼마였는지" 근사할
    때 쓴다 — DART엔 실제 매수단가가 없으니(실측 확인) 대신 공시일 종가로
    추정한다. 주말/공휴일이면 그 이전 거래일 종가를 쓰므로 실제 체결가와
    다를 수 있음 — 반드시 "추정치"로 표시할 것.
    """
    try:
        target = dt.datetime.strptime(date_str, "%Y-%m-%d").date()
        start = target - dt.timedelta(days=10)  # 연휴 대비 넉넉히
        end = target + dt.timedelta(days=1)
        hist = yf.Ticker(krx_ticker).history(
            start=start.isoformat(), end=end.isoformat(), interval="1d"
        )
        closes = hist["Close"].dropna()
        if closes.empty:
            return None
        on_or_before = closes[closes.index.date <= target]
        if on_or_before.empty:
            return None
        return float(on_or_before.iloc[-1])
    except Exception:
        logger.exception("KRX %s 종가 조회 실패 (%s)", date_str, krx_ticker)
        return None
