"""단발성 실행 엔트리포인트: 전체 파이프라인을 한 번 수행한다.

수집 -> 계산 -> 저장.
반복 실행은 scheduler.py(소스별 다른 주기)가 담당한다.
"""

from __future__ import annotations

import logging

import db
from collectors.equities import collect_equity_changes
from collectors.krx import fetch_last_close
from collectors.macro import collect_macro_changes
from collectors.tokenized import collect_token_prices
from config import SYMBOLS
from models.scoring import compute_prediction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_once() -> None:
    equity_changes = collect_equity_changes()
    macro_changes = collect_macro_changes()
    token_prices = collect_token_prices()

    for symbol, meta in SYMBOLS.items():
        last_close = fetch_last_close(meta["krx_ticker"])
        token_price = token_prices.get(f"{symbol}_token")

        if last_close is None:
            logger.error("%s: KRX 종가 조회 실패 — 예측 건너뜀", symbol)
            db.log_admin_event(symbol, "error", "KRX last close fetch failed")
            continue

        token_change_percent = None
        if token_price is not None and last_close:
            # TODO: basis_offsets 테이블의 보정값을 여기서 반영 (docs/PRD.md 3.1)
            token_change_percent = (token_price - last_close) / last_close * 100

        prediction = compute_prediction(
            symbol=symbol,
            current_price=last_close,
            token_change_percent=token_change_percent,
            equity_changes=equity_changes,
            macro_changes=macro_changes,
        )

        db.insert("predictions", prediction.to_row())
        logger.info(
            "%s: %.0f -> %.0f (%.2f%%)",
            symbol,
            prediction.current_price,
            prediction.predicted_price,
            prediction.change_percent,
        )

    db.log_admin_event("pipeline", "ok", "run_once completed")


if __name__ == "__main__":
    run_once()
