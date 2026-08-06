"""단발성 실행 엔트리포인트: 전체 파이프라인을 한 번 수행한다.

수집 -> 계산 -> 저장.
반복 실행은 scheduler.py(소스별 다른 주기)가 담당한다.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

import db
from collectors.equities import collect_equity_changes
from collectors.flows import collect_daily_flows
from collectors.krx import fetch_intraday_price, fetch_last_close_with_date, fetch_previous_close
from collectors.macro import collect_macro_changes
from collectors.market_hours import KST, get_session, has_real_price_feed
from collectors.tokenized import BYBIT_SYMBOLS, collect_token_prices, fetch_bybit_close_at_krx_close
from config import SYMBOLS
from models.scoring import compute_prediction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_last_flows_date: str | None = None  # 하루 1회만 스크래핑하기 위한 가드 (config.INTERVAL_FLOWS_SECONDS)

# Supabase를 아직 안 붙였을 때도 웹에서 실제 값을 볼 수 있도록, 계산 결과를
# apps/web이 바로 읽는 JSON 파일로도 내보낸다. Supabase 연동 후에는
# 이 파일 대신 predictions 테이블을 읽도록 apps/web 쪽만 바꾸면 됨.
_WEB_SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "apps" / "web" / "public" / "predictions.json"

# 백테스트 방향적중률(docs/PRD.md 4.2) — recentAccuracy 표시에 사용.
# TODO: prediction_accuracy 테이블이 쌓이면 그 실측치로 교체할 것.
_BACKTEST_DIRECTION_ACCURACY = {"SAMSUNG": 63, "SKHYNIX": 71}


def _write_web_snapshot(rows: list[dict]) -> None:
    try:
        _WEB_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _WEB_SNAPSHOT_PATH.write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("웹 스냅샷 저장: %s", _WEB_SNAPSHOT_PATH)
    except Exception:
        logger.exception("웹 스냅샷 저장 실패 (%s)", _WEB_SNAPSHOT_PATH)


def _maybe_collect_flows() -> None:
    """공매도/수급은 장마감 후 하루 1회만 갱신되므로, run_once가 몇 분마다
    호출돼도 실제 스크래핑은 날짜가 바뀔 때만 수행한다 (Naver 과다호출 방지).
    """
    global _last_flows_date
    today = dt.datetime.now(KST).date().isoformat()  # KRX 거래일은 KST 기준
    if today == _last_flows_date:
        return
    for symbol, meta in SYMBOLS.items():
        flows = collect_daily_flows(meta["krx_code"])
        for metric, value in flows.items():
            if value is not None:
                db.insert("raw_snapshots", {"source": f"flows:{symbol}:{metric}", "value": value})
        logger.info("%s: 수급 데이터 수집 — %s", symbol, flows)
    _last_flows_date = today


def run_once() -> None:
    equity_changes = collect_equity_changes()
    macro_changes = collect_macro_changes()
    token_prices = collect_token_prices()
    _maybe_collect_flows()  # 아직 scoring에는 미반영 — raw_snapshots에만 적재 (docs/PRD.md 4.3)

    # market_hours.get_session()과 동일하게 KST 기준으로 판정 (실행 서버가
    # 다른 시간대여도 일관되게 나오도록 — 예전엔 로컬 시간대 기준이라 어긋날 수 있었음)
    is_weekend = dt.datetime.now(KST).weekday() >= 5
    session = get_session()
    show_real_price = has_real_price_feed(session)  # 지금은 정규장(open)만 True
    web_rows: list[dict] = []

    logger.info("KRX 세션 상태: %s (실제가 표시=%s)", session, show_real_price)

    for symbol, meta in SYMBOLS.items():
        # ── 1) 실제가를 보여줄 수 있는 구간(정규장 운영 중): 예측하지 않고
        #    실시간 체결가를 그대로 보여준다 (docs/PRD.md 3.4 — 사용자 요청으로 확정).
        if show_real_price:
            live_price = fetch_intraday_price(meta["krx_ticker"])
            prev_close, _ = fetch_previous_close(meta["krx_ticker"])
            if live_price is None or prev_close is None:
                logger.error("%s: 실시간가/전일종가 조회 실패", symbol)
                db.log_admin_event(symbol, "error", "intraday/previous close fetch failed")
                continue

            change_percent_today = (live_price - prev_close) / prev_close * 100
            db.insert(
                "actual_prices",
                {
                    "symbol": symbol,
                    "price": live_price,
                    "session": "regular",
                    "trade_date": dt.datetime.now(KST).date().isoformat(),
                },
            )
            logger.info("%s: 실제가 %.0f (전일比 %.2f%%) — 예측 생략", symbol, live_price, change_percent_today)

            web_rows.append(
                {
                    "symbol": symbol,
                    "name": meta["name"],
                    "ticker": meta["krx_code"],
                    "currentPrice": round(live_price),
                    "predictedPrice": round(live_price),  # 실제가 = 추정 불필요
                    "changePercent": round(change_percent_today, 2),
                    "confidence": 100.0,
                    "probabilityUp": 100.0 if change_percent_today >= 0 else 0.0,
                    "rangeLow": round(live_price),
                    "rangeHigh": round(live_price),
                    "factors": [],
                    "recentAccuracy": _BACKTEST_DIRECTION_ACCURACY.get(symbol, 0),
                    "asOf": dt.datetime.now().isoformat(),
                    "isWeekend": False,
                    "isLowSample": False,
                    "sampleSizeDays": 0,
                    "isEstimate": False,
                }
            )
            continue

        # ── 2) 실제가가 없는 구간(장외/휴장/주말): 지금까지 만든 예측 로직 사용.
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
            base_token_price = fetch_bybit_close_at_krx_close(BYBIT_SYMBOLS[symbol], trade_date)
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

        web_rows.append(
            {
                "symbol": symbol,
                "name": meta["name"],
                "ticker": meta["krx_code"],
                "currentPrice": prediction.current_price,
                "predictedPrice": prediction.predicted_price,
                "changePercent": prediction.change_percent,
                "confidence": prediction.confidence,
                "probabilityUp": prediction.probability_up,
                "rangeLow": prediction.range_low,
                "rangeHigh": prediction.range_high,
                "factors": [
                    {"label": f.label, "contribution": f.contribution}
                    for f in prediction.factors
                ],
                "recentAccuracy": _BACKTEST_DIRECTION_ACCURACY.get(symbol, 0),
                "asOf": dt.datetime.now().isoformat(),
                "isWeekend": is_weekend,
                "isLowSample": prediction.is_low_sample,
                "sampleSizeDays": prediction.sample_size_days,
                "isEstimate": True,
            }
        )

    if web_rows:
        _write_web_snapshot(web_rows)

    db.log_admin_event("pipeline", "ok", "run_once completed")


if __name__ == "__main__":
    run_once()
