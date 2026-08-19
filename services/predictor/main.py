"""단발성 실행 엔트리포인트: 전체 파이프라인을 한 번 수행한다.

수집 -> 계산 -> 저장.
반복 실행은 scheduler.py(소스별 다른 주기)가 담당한다.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

import accuracy_log
import db
import last_real_price
import pef_flow_tracker
import pef_tracker
import token_change_cache
from collectors.adr import collect_adr_changes
from collectors.equities import collect_equity_changes
from collectors.flows import collect_daily_flows
from collectors.krx import (
    fetch_after_hours_price,
    fetch_intraday_price,
    fetch_last_close_with_date,
    fetch_previous_close,
)
from collectors.macro import collect_macro_changes
from collectors.market_hours import KST, get_session, has_real_price_feed
from collectors.tokenized import BYBIT_SYMBOLS, collect_token_prices, fetch_bybit_close_at_krx_close
from config import SYMBOLS
from models.scoring import compute_prediction

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 하루 1회만 도는 작업들(공매도/수급, PEF 지분공시)의 "마지막 실행 날짜"
# 가드 — 실측으로 발견한 버그: 예전엔 모듈 전역 변수(메모리)였는데, 로컬
# scheduler.py(오래 켜져있는 프로세스)에선 맞게 동작해도 GitHub Actions는
# 매 실행마다 python main.py를 완전히 새 프로세스로 띄우기 때문에 메모리
# 변수는 매번 초기화돼 가드가 사실상 무력화됨 — 하루 144번(10분 간격)
# KRX 로그인 + 네이버 스크래핑이 벌어지고 있었음(2026-08-08 확인). git에
# 커밋되는 파일로 영속화해서 accuracy_log.py와 같은 방식으로 고침. 여러
# 일일 작업이 키만 다르게 같은 파일을 공유한다.
_DAILY_STATE_PATH = Path(__file__).resolve().parent / "data" / "flows_state.json"


def _load_last_run_date(key: str) -> str | None:
    try:
        if not _DAILY_STATE_PATH.exists():
            return None
        return json.loads(_DAILY_STATE_PATH.read_text(encoding="utf-8")).get(key)
    except Exception:
        logger.exception("%s 읽기 실패 — 오늘 다시 수집함", _DAILY_STATE_PATH)
        return None


def _save_last_run_date(key: str, date_str: str) -> None:
    try:
        _DAILY_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        existing = {}
        if _DAILY_STATE_PATH.exists():
            try:
                existing = json.loads(_DAILY_STATE_PATH.read_text(encoding="utf-8"))
            except Exception:
                existing = {}
        existing[key] = date_str
        _DAILY_STATE_PATH.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        logger.exception("%s 저장 실패", _DAILY_STATE_PATH)


# Supabase를 아직 안 붙였을 때도 웹에서 실제 값을 볼 수 있도록, 계산 결과를
# apps/web이 바로 읽는 JSON 파일로도 내보낸다. Supabase 연동 후에는
# 이 파일 대신 predictions 테이블을 읽도록 apps/web 쪽만 바꾸면 됨.
_WEB_SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "apps" / "web" / "public" / "predictions.json"
_WEB_ACCURACY_PATH = Path(__file__).resolve().parents[2] / "apps" / "web" / "public" / "accuracy-history.json"
_WEB_PEF_PATH = Path(__file__).resolve().parents[2] / "apps" / "web" / "public" / "pef-activity.json"
_WEB_PEF_FLOW_PATH = Path(__file__).resolve().parents[2] / "apps" / "web" / "public" / "pef-flow-activity.json"
_WEB_PEF_COMBINED_PATH = Path(__file__).resolve().parents[2] / "apps" / "web" / "public" / "pef-combined-signal.json"

# 실제 기록(accuracy_log)이 아직 부족할 때 쓰는 초기 폴백 — 2026-08-06
# 40일 표본 백테스트 방향적중률 (docs/PRD.md 4.2). 실제 예측->확정 사이클이
# 쌓이면 accuracy_log.compute_recent_accuracy_percent()가 우선한다.
_BACKTEST_DIRECTION_ACCURACY = {"SAMSUNG": 63, "SKHYNIX": 71}


def _recent_accuracy(symbol: str) -> tuple[float, bool]:
    """(정확도%, 실제기록기반여부). 실제 기록이 있으면 그걸 쓰고,
    없으면(서비스 초기) 백테스트 추정치로 대체한다."""
    real = accuracy_log.compute_recent_accuracy_percent(symbol)
    if real is not None:
        return real, True
    return float(_BACKTEST_DIRECTION_ACCURACY.get(symbol, 0)), False


def _load_existing_snapshot() -> dict[str, dict]:
    """symbol별 마지막으로 성공한 row. 이번 실행에서 한 종목만 실패해도
    (예: KRX 조회 일시 오류) 다른 종목까지 화면에서 같이 사라지지 않도록,
    새로 못 구한 symbol은 이전 값을 그대로 유지하기 위해 씀."""
    try:
        if not _WEB_SNAPSHOT_PATH.exists():
            return {}
        rows = json.loads(_WEB_SNAPSHOT_PATH.read_text(encoding="utf-8"))
        return {r["symbol"]: r for r in rows}
    except Exception:
        logger.exception("기존 웹 스냅샷 읽기 실패 — 빈 상태로 시작")
        return {}


def _write_web_snapshot(rows: list[dict]) -> None:
    try:
        existing = _load_existing_snapshot()
        existing.update({r["symbol"]: r for r in rows})  # 이번 실행 성공분만 갱신
        merged = list(existing.values())
        _WEB_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _WEB_SNAPSHOT_PATH.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info("웹 스냅샷 저장: %s (%d개 종목)", _WEB_SNAPSHOT_PATH, len(merged))
    except Exception:
        logger.exception("웹 스냅샷 저장 실패 (%s)", _WEB_SNAPSHOT_PATH)


def _maybe_collect_flows() -> None:
    """공매도/수급은 장마감 후 하루 1회만 갱신되므로, run_once가 몇 분마다
    호출돼도 실제 스크래핑(+ KRX 로그인)은 날짜가 바뀔 때만 수행한다 (Naver/
    KRX 과다호출·계정 이상탐지 방지). 마지막 수집 날짜는 git에 커밋되는
    파일로 영속화한다 — 프로세스 메모리에만 두면 매 실행마다 새 프로세스인
    GitHub Actions에서 가드가 무력화되기 때문(2026-08-08 실측으로 발견:
    하루 144번 로그인되고 있었음).
    """
    today = dt.datetime.now(KST).date().isoformat()  # KRX 거래일은 KST 기준
    if today == _load_last_run_date("last_flows_date"):
        return
    for symbol, meta in SYMBOLS.items():
        flows = collect_daily_flows(meta["krx_code"])
        for metric, value in flows.items():
            if value is not None:
                db.insert("raw_snapshots", {"source": f"flows:{symbol}:{metric}", "value": value})
        logger.info("%s: 수급 데이터 수집 — %s", symbol, flows)
    _save_last_run_date("last_flows_date", today)


def _maybe_collect_pef_activity() -> None:
    """PEF 지분공시(DART)도 하루 1회면 충분한 이벤트라 같은 가드를 쓴다
    (5%룰 공시는 실시간성이 필요 없고, DART 요청 수를 아낄 이유도 있음)."""
    today = dt.datetime.now(KST).date().isoformat()
    if today == _load_last_run_date("last_pef_date"):
        return
    try:
        pef_tracker.export_pef_activity()
    except Exception:
        logger.exception("PEF 활동 랭킹 수집 실패")
    _save_last_run_date("last_pef_date", today)


def _maybe_collect_pef_flow_activity() -> None:
    """KRX 투자자별(사모) 수급 이례치도 장마감 후 하루 1회면 충분하다."""
    today = dt.datetime.now(KST).date().isoformat()
    if today == _load_last_run_date("last_pef_flow_date"):
        return
    try:
        pef_flow_tracker.export_pef_flow_activity()
    except Exception:
        logger.exception("PEF 수급 이례치 수집 실패")
    _save_last_run_date("last_pef_flow_date", today)


def _maybe_collect_pef_combined_signal() -> None:
    """사모+기관 복합 수급 신호도 하루 1회. 별도 가드 키를 써서 위 단일
    신호 수집과 독립적으로 재시도할 수 있게 한다."""
    today = dt.datetime.now(KST).date().isoformat()
    if today == _load_last_run_date("last_pef_combined_date"):
        return
    try:
        pef_flow_tracker.export_combined_signal_activity()
    except Exception:
        logger.exception("PEF 복합 수급 신호 수집 실패")
    _save_last_run_date("last_pef_combined_date", today)


def run_once() -> None:
    equity_changes = collect_equity_changes()
    macro_changes = collect_macro_changes()
    token_prices = collect_token_prices()
    adr_changes = collect_adr_changes()  # SK하이닉스 나스닥 ADR(SKHY) — collectors/adr.py 참고
    _maybe_collect_flows()  # 아직 scoring에는 미반영 — raw_snapshots에만 적재 (docs/PRD.md 4.3)
    _maybe_collect_pef_activity()
    _maybe_collect_pef_flow_activity()
    _maybe_collect_pef_combined_signal()

    # market_hours.get_session()과 동일하게 KST 기준으로 판정 (실행 서버가
    # 다른 시간대여도 일관되게 나오도록 — 예전엔 로컬 시간대 기준이라 어긋날 수 있었음)
    is_weekend = dt.datetime.now(KST).weekday() >= 5
    session = get_session()
    show_real_price = has_real_price_feed(session)  # 지금은 정규장(open)만 True
    web_rows: list[dict] = []

    logger.info("KRX 세션 상태: %s (실제가 표시=%s)", session, show_real_price)

    for symbol, meta in SYMBOLS.items():
        # ── 1) 실제가를 보여줄 수 있는 구간(정규장/장전·장후 시간외): 예측하지
        #    않고 실제 체결가를 그대로 보여준다 (docs/PRD.md 3.4).
        if show_real_price:
            if session == "open":
                live_price = fetch_intraday_price(meta["krx_ticker"])
            else:  # pre_market / post_market — 시간외 단일가
                live_price = fetch_after_hours_price(meta["krx_ticker"])
            prev_close, _ = fetch_previous_close(meta["krx_ticker"])
            if live_price is None or prev_close is None:
                logger.error("%s: 실제가/전일종가 조회 실패 (세션=%s)", symbol, session)
                db.log_admin_event(symbol, "error", f"real price fetch failed (session={session})")
                continue

            change_percent_today = (live_price - prev_close) / prev_close * 100
            today_str = dt.datetime.now(KST).date().isoformat()
            db.insert(
                "actual_prices",
                {
                    "symbol": symbol,
                    "price": live_price,
                    "session": session,
                    "trade_date": today_str,
                },
            )
            # closed 세션(장마감 후)에서 "현재가"를 이 값으로 보여줄 수 있게
            # 로컬(→git→CI)에도 캐싱해둔다 — Supabase는 CI에서 쓰기 전용이라
            # 여기서 다시 읽어올 수 없어서 별도 캐시가 필요하다.
            last_real_price.save(symbol, price=live_price, session=session, trade_date=today_str)
            logger.info(
                "%s: 실제가 %.0f (전일比 %.2f%%, 세션=%s) — 예측 생략",
                symbol, live_price, change_percent_today, session,
            )

            accuracy_pct, accuracy_is_real = _recent_accuracy(symbol)
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
                    "recentAccuracy": accuracy_pct,
                    "isRealAccuracy": accuracy_is_real,
                    "asOf": dt.datetime.now(KST).isoformat(),
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

        # Bybit가 GitHub Actions(클라우드 IP)에서 구조적으로 막혀 있어
        # (token_change_cache.py 참고) 여기서 실패하는 게 정상적으로 자주
        # 있는 일이다 — 로컬이 최근 저장해둔 값이 신선하면 그걸로 대체한다.
        if token_change_percent is not None:
            token_change_cache.save(symbol, token_change_percent)
        else:
            cached = token_change_cache.load_fresh(symbol)
            if cached is not None:
                token_change_percent = cached
                logger.info("%s: Bybit 직접 조회 실패 — 로컬 캐시값 사용 (%.2f%%)", symbol, cached)

        prediction = compute_prediction(
            symbol=symbol,
            current_price=last_close,
            token_change_percent=token_change_percent,
            adr_change_percent=adr_changes.get(symbol),
            equity_changes=equity_changes,
            macro_changes=macro_changes,
        )
        prediction.is_weekend = is_weekend  # compute_prediction은 시간 정보를 모르므로 여기서 채움

        # 지난번 예측(pending)이 있었고 그게 예측했던 종가가 이번에 새로
        # 확정됐으면(trade_date가 바뀌었으면) 정확도 기록에 남기고, 이번
        # 예측을 새 pending으로 교체한다 (accuracy_log.py 참고).
        accuracy_log.reconcile_and_store(
            symbol=symbol,
            trade_date=trade_date,
            last_close=last_close,
            predicted_price=prediction.predicted_price,
            change_percent=prediction.change_percent,
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

        # 화면에 보여줄 "현재가"는 가능하면 last_close(정규장 종가)보다 더
        # 신선한 정보를 쓴다 — 오늘 장후 시간외(16:00~18:00)에서 이미 확보한
        # 실제 체결가가 있으면 그걸 우선한다. 실측으로 발견한 문제: 종전엔
        # closed 세션으로 넘어가는 순간 이 실제 시간외가를 버리고 몇 시간
        # 전 정규장 종가를 "현재가"라고 표시하고 있었다. 예측 계산 자체
        # (score 산출)는 학습 방식(정규장 종가→다음 정규장 종가)과 어긋나지
        # 않도록 last_close 기준을 그대로 쓴다.
        anchor_price = last_real_price.load_post_market_anchor(symbol, trade_date) or last_close

        # 2026-08-19 실측으로 발견한 버그: changePercent를 anchor_price 기준으로
        # 다시 계산했더니, 장후 시간외에 정규장 종가 대비 크게 움직인 날엔
        # 부호까지 뒤집혀 보였다(예: 모델은 last_close 대비 +0.57% 상승 예측
        # 했는데, 그날 시간외가 이미 +9.6% 뛰어있어서 anchor 대비로는
        # -8.24% "급락 예측"처럼 표시됨 — 모델이 실제로 계산하지 않은 숫자를
        # 보여준 셈). currentPrice(가장 신선한 실제가)와 changePercent(모델이
        # last_close 기준으로 실제 계산한 등락률)는 기준점이 다르다는 걸
        # 감안하고 각각 그대로 보여준다 — 서로 재계산해서 섞지 않는다.
        accuracy_pct, accuracy_is_real = _recent_accuracy(symbol)
        web_rows.append(
            {
                "symbol": symbol,
                "name": meta["name"],
                "ticker": meta["krx_code"],
                "currentPrice": round(anchor_price),
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
                "recentAccuracy": accuracy_pct,
                "isRealAccuracy": accuracy_is_real,
                "asOf": dt.datetime.now(KST).isoformat(),
                "isWeekend": is_weekend,
                "isLowSample": prediction.is_low_sample,
                "sampleSizeDays": prediction.sample_size_days,
                "isEstimate": True,
            }
        )

    if web_rows:
        _write_web_snapshot(web_rows)

    accuracy_log.export_history_for_web(_WEB_ACCURACY_PATH)
    pef_tracker.export_for_web(_WEB_PEF_PATH)
    pef_flow_tracker.export_for_web(_WEB_PEF_FLOW_PATH)
    pef_flow_tracker.export_combined_signal_for_web(_WEB_PEF_COMBINED_PATH)

    db.log_admin_event("pipeline", "ok", "run_once completed")


if __name__ == "__main__":
    run_once()
