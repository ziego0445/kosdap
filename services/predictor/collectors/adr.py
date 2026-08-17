"""3차 신호: SK하이닉스 나스닥 상장 ADR(SKHY).

Bybit 토큰화 선물(collectors/tokenized.py)보다 신뢰도가 높은 장외시간
프록시 — SKHY는 실제 나스닥 글로벌 셀렉트마켓(NasdaqGS)에 정식 상장된
종목이라 정규 거래소 수준의 가격발견/유동성이 있다(2026-08-17 실측:
longName="SK hynix Inc.", exchange=NasdaqGS, 일평균 거래량 4천만주대).
원주(000660) 대비 ADR 비율은 실측으로 약 1:7 확인했고(같은 날짜 종가
기준 KRX 1,645,000원 vs SKHY $166.33×환율 ≈ 235,300원), 재정거래로
정합성이 유지되는 정식 상장 종목이라 판단해 채택했다.

삼성전자 쪽 대응 티커(SSNLF)도 있지만 OTC Pink 상장이고 실측 확인 결과
평균거래량 0, 5거래일 연속 가격이 아예 안 움직여서(가격발견 기능
없음) 신호로 쓸 수 없다 — 그래서 SK하이닉스만 취급한다.

미국 정규장(정규 09:30~16:00 ET, 프리/애프터마켓 포함해도 KRX 폐장
시간대와 완전히 겹치진 않음) 시간대에만 갱신되므로 24/7은 아니고,
Bybit 토큰 신호와 상호보완 관계로 본다.
"""

from __future__ import annotations

from ._util import pct_change

ADR_SYMBOLS = {"SKHYNIX": "SKHY"}  # 삼성전자는 대응 ADR 유동성 없어 제외 (위 설명 참고)


def collect_adr_changes() -> dict[str, float | None]:
    """종목별 ADR 전일 대비 변동률(%). 원주와 통화가 달라도(USD vs KRW)
    등락률(%) 비교엔 무관하므로(퍼센트는 통화 독립적) 환산 없이 그대로 쓴다."""
    return {symbol: pct_change(ticker) for symbol, ticker in ADR_SYMBOLS.items()}
