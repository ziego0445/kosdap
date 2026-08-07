"""3차 신호: 외국인/기관 순매수, 공매도비율 — 하루 1회, 장마감 후 갱신.

실측 결과 네이버페이 증권(finance.naver.com/item/frgn.naver)에서 종목별
외국인/기관 순매매량(주식수)을 스크래핑으로 확인함 (2026-08-06).

공매도비율은 KRX Open API(인증키 방식)엔 상품 자체가 없음을 실측 확인함
(2026-08-07, data-dbg.krx.co.kr에 sto 카테고리는 401/공매도 카테고리는
전부 404). data.krx.co.kr 내부 통계 화면은 "사이트 로그인 세션"이 있어야
JSON을 내려주는데(익명 세션은 빈 응답), pykrx 라이브러리가 이 로그인
흐름(KRX_ID/KRX_PW 환경변수)까지 구현해둬서 그걸 그대로 씀 — 실측 확인
(2026-08-07): 삼성전자 공매도비율 1.8~16.5% 범위로 정상 수신됨.

주의: 비공식 스크래핑이라 페이지/로그인 흐름이 바뀌면 깨질 수 있음. 표에
실린 숫자는 KRW 금액이 아니라 "순매매 주식수"라, 필요하면 그날 종가를
곱해 금액으로 환산할 것.
"""

from __future__ import annotations

import datetime as dt
import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

NAVER_FRGN_URL = "https://finance.naver.com/item/frgn.naver"

_SHORT_LOOKBACK_DAYS = 10  # 공매도 데이터는 보통 T-2 근처까지만 공개되므로 넉넉히 잡음


def _parse_signed_int(text: str) -> int | None:
    text = text.replace(",", "").replace("+", "")
    if not text or text in ("-", ""):
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _fetch_short_selling_ratio(krx_code: str) -> float | None:
    """공매도비율(%) = 최근 거래일 공매도거래량 / 그날 전체거래량 * 100.

    data.krx.co.kr 로그인 세션이 필요해 pykrx(KRX_ID/KRX_PW 환경변수)를 쓴다.
    config.py에서 이미 load_dotenv()가 실행된 뒤에야(=main.py가 config를
    import한 뒤에야) 세션을 만들어야 하므로 지연 임포트한다.
    """
    try:
        from pykrx import stock  # 지연 임포트 (위 docstring 참고)

        end = dt.date.today()
        start = end - dt.timedelta(days=_SHORT_LOOKBACK_DAYS)
        d1, d2 = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")

        short_df = stock.get_shorting_status_by_date(d1, d2, krx_code)
        if short_df.empty:
            logger.warning("공매도비율(%s): 응답 비어있음", krx_code)
            return None

        ohlcv_df = stock.get_market_ohlcv(d1, d2, krx_code)
        if ohlcv_df.empty:
            return None

        merged = short_df.join(ohlcv_df[["거래량"]], how="inner", lsuffix="_short")
        if merged.empty:
            return None

        last = merged.iloc[-1]
        total_volume = last["거래량"]
        if not total_volume:
            return None
        return round(float(last["거래량_short"]) / float(total_volume) * 100, 2)
    except Exception:
        logger.exception("공매도비율 수집 실패 (%s)", krx_code)
        return None


def collect_daily_flows(krx_code: str) -> dict[str, float | None]:
    """krx_code는 순수 종목코드(예: '005930'), '.KS' 접미사 없이."""
    short_selling_ratio = _fetch_short_selling_ratio(krx_code)

    try:
        resp = requests.get(
            NAVER_FRGN_URL,
            params={"code": krx_code},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=10,
        )
        resp.raise_for_status()
        resp.encoding = "euc-kr"
        soup = BeautifulSoup(resp.text, "html.parser")
        table = soup.find_all("table", class_="type2")[1]
        for tr in table.find_all("tr"):
            cells = [td.get_text(strip=True) for td in tr.find_all("td")]
            # [날짜, 종가, 전일비, 등락률, 거래량, 기관순매매량, 외국인순매매량, 외국인보유주수, 외국인보유율]
            if len(cells) != 9:
                continue
            return {
                "institution_net_shares": _parse_signed_int(cells[5]),
                "foreign_net_shares": _parse_signed_int(cells[6]),
                "foreign_holding_ratio_percent": (
                    float(cells[8].replace("%", "")) if "%" in cells[8] else None
                ),
                "short_selling_ratio": short_selling_ratio,
            }
        logger.warning("collect_daily_flows(%s): 파싱 가능한 row를 못 찾음", krx_code)
    except Exception:
        logger.exception("collect_daily_flows(%s) failed", krx_code)

    return {
        "institution_net_shares": None,
        "foreign_net_shares": None,
        "foreign_holding_ratio_percent": None,
        "short_selling_ratio": short_selling_ratio,
    }
