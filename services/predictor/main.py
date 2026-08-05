"""단발성 실행 엔트리포인트: 전체 파이프라인을 한 번 수행한다.

수집 -> 계산 -> 저장.
반복 실행은 scheduler.py(소스별 다른 주기)가 담당한다.
"""

from __future__ import annotations

import logging

import db
from collectors.equities import collect_equity_changes
from collectors.krx import fetch_last_close_with_date
from collectors.macro import collect_macro_changes
from collectors.tokenized import BYBIT_SYMBOLS, collect_token_prices, fetch_bybit_daily_close
from config import SYMBOLS
from models.scoring import compute_prediction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_once() -> None:
    equity_changes = collect_equity_changes()
    macro_changes = collect_macro_changes()
    token_prices = collect_token_prices()

    for symbol, meta in SYMBOLS.items():
        last_close, trade_date = fetch_last_close_with_date(meta["krx_ticker"])
        token_price = token_prices.get(f"{symbol}_token")

        if last_close is None:
            logger.error("%s: KRX 종가 조회 실패 — 예측 건너뜀", symbol)
            db.log_admin_event(symbol, "error", "KRX last close fetch failed")
            continue

        # 토큰가(USDT)와 KRX 종가(KRW)는 통화가 달라 직접 뺄셈하면 안 된다
        # (실측 확인된 버그). "KRX 마감일 토큰 종가" 대비 "현재 토큰가"의
        # 변동률(USDT/USDT, 같은 통화)을 구해서 그 비율만 KRW 종가에 적용한다.
        token_change_percent = None
        if token_price is not None and trade_date is not None:
            base_token_price = fetch_bybit_daily_close(BYBIT_SYMBOLS[symbol], trade_date)
            if base_token_price:
                token_change_percent = (token_price - base_token_price) / base_token_price * 100
            else:
                logger.warning(
                    "%s: 기준 토큰가(%s @ %s) 조회 실패 — token 신호 제외",
                    symbol,
                    BYBIT_SYMBOLS[symbol],
                    trade_date,
                )

        prediction = compute_prediction(
            symbol=symbol,
            current_price=last_close,
            token_change_percent=token_change_percent,
            equity_changes=equity_changes,
            macro_changes=macro_changes,
        )

        db.insert("predictions", prediction.to_row())
        logger.info(
            "%s: %.0f -> %.0f (%.2f%%) [token_change=%s]",
            symbol,
            prediction.current_price,
            prediction.predicted_price,
            prediction.change_percent,
            f"{token_change_percent:.2f}%" if token_change_percent is not None else "N/A",
        )

    db.log_admin_event("pipeline", "ok", "run_once completed")


if __name__ == "__main__":
    run_once()
