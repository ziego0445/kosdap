"""3차 신호: 외국인/기관 순매수, 공매도비율 — 하루 1회, 장마감 후 갱신.

실측 결과 네이버페이 증권(finance.naver.com/item/frgn.naver)에서 종목별
외국인/기관 순매매량(주식수)을 스크래핑으로 확인함 (2026-08-06). 공매도
비율은 네이버에 해당 페이지가 없어(404 확인) 여전히 스텁 — KRX 정보데이터
시스템(data.krx.co.kr) 공식 API 연동이 필요하다.

주의: 비공식 스크래핑이라 페이지 구조가 바뀌면 깨질 수 있음. 표에 실린
숫자는 KRW 금액이 아니라 "순매매 주식수"라, 필요하면 그날 종가를 곱해
금액으로 환산할 것.
"""

from __future__ import annotations

import logging

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

NAVER_FRGN_URL = "https://finance.naver.com/item/frgn.naver"


def _parse_signed_int(text: str) -> int | None:
    text = text.replace(",", "").replace("+", "")
    if not text or text in ("-", ""):
        return None
    try:
        return int(text)
    except ValueError:
        return None


def collect_daily_flows(krx_code: str) -> dict[str, float | None]:
    """krx_code는 순수 종목코드(예: '005930'), '.KS' 접미사 없이."""
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
                "short_selling_ratio": None,  # TODO: KRX 정보데이터시스템 연동 필요
            }
        logger.warning("collect_daily_flows(%s): 파싱 가능한 row를 못 찾음", krx_code)
    except Exception:
        logger.exception("collect_daily_flows(%s) failed", krx_code)

    return {
        "institution_net_shares": None,
        "foreign_net_shares": None,
        "foreign_holding_ratio_percent": None,
        "short_selling_ratio": None,
    }
