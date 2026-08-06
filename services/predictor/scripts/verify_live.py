"""라이브 보정 검증: "지금 이 순간을 모델이 예측했다면 실제와 얼마나
가까웠을까"를 실시간으로 확인한다.

정규장 운영 중엔 main.py가 예측을 아예 건너뛰고 실제가를 보여주므로
(docs/PRD.md 5.1), 예측 로직 자체를 실전처럼 검증할 기회가 마감 후/주말뿐
이었다. 이 스크립트는 장중에도 "어제 종가를 기준(current_price)으로
지금 이 순간의 실시간 프록시 입력을 넣으면 모델이 뭘 예측하는지"를 계산해
실제 실시간가와 나란히 비교한다 — 장 마감을 기다리지 않고도 모델 보정을
할 수 있게 해준다.

사용:
    python scripts/verify_live.py            # 5회 (기본), 30초 간격
    python scripts/verify_live.py --n 10 --interval 15
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

# Windows 콘솔 기본 코드페이지(cp949)는 이모지 등 일부 유니코드를 못 담아서
# print()가 UnicodeEncodeError로 죽을 수 있음 — 출력 인코딩을 명시적으로 UTF-8로.
sys.stdout.reconfigure(encoding="utf-8")

# scripts/는 services/predictor의 하위 폴더라, collectors/models 패키지를
# 임포트하려면 services/predictor 자체를 sys.path에 넣어줘야 한다.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from collectors.equities import collect_equity_changes
from collectors.krx import fetch_intraday_price, fetch_previous_close
from collectors.macro import collect_macro_changes
from collectors.market_hours import get_session, has_real_price_feed
from collectors.tokenized import BYBIT_SYMBOLS, collect_token_prices, fetch_bybit_close_at_krx_close
from config import SYMBOLS
from models.scoring import compute_prediction

logging.basicConfig(level=logging.WARNING)  # 하위 collector의 INFO 로그는 숨기고 결과만 보여줌


def run_once_check() -> dict[str, dict]:
    equity_changes = collect_equity_changes()
    macro_changes = collect_macro_changes()
    token_prices = collect_token_prices()

    results: dict[str, dict] = {}
    for symbol, meta in SYMBOLS.items():
        actual_now = fetch_intraday_price(meta["krx_ticker"])
        prev_close, prev_date = fetch_previous_close(meta["krx_ticker"])
        if actual_now is None or prev_close is None or prev_date is None:
            results[symbol] = {"error": "가격 조회 실패"}
            continue

        token_price = token_prices.get(f"{symbol}_token")
        token_change = None
        if token_price is not None:
            base = fetch_bybit_close_at_krx_close(BYBIT_SYMBOLS[symbol], prev_date)
            if base:
                token_change = (token_price - base) / base * 100

        pred = compute_prediction(
            symbol=symbol,
            current_price=prev_close,
            token_change_percent=token_change,
            equity_changes=equity_changes,
            macro_changes=macro_changes,
        )

        actual_change_pct = (actual_now - prev_close) / prev_close * 100
        error_pct = (pred.predicted_price - actual_now) / actual_now * 100

        results[symbol] = {
            "prev_close": prev_close,
            "actual_now": actual_now,
            "actual_change_pct": round(actual_change_pct, 2),
            "predicted_price": pred.predicted_price,
            "predicted_change_pct": pred.change_percent,
            "error_pct": round(error_pct, 2),
            "dir_match": (pred.change_percent >= 0) == (actual_change_pct >= 0),
        }
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=5)
    parser.add_argument("--interval", type=int, default=30, help="반복 간 대기 초")
    args = parser.parse_args()

    session = get_session()
    if not has_real_price_feed(session):
        print(f"⚠ 지금 KRX 세션 상태: {session} — 실제가가 없어서 비교 기준이 없습니다. "
              f"정규장(09:00~15:30 KST) 중에 돌려야 의미있는 검증이 됩니다.")
        return

    all_runs: list[dict[str, dict]] = []
    for i in range(args.n):
        print(f"\n[{i + 1}/{args.n}] 실행 중...")
        result = run_once_check()
        all_runs.append(result)
        for symbol, r in result.items():
            if "error" in r:
                print(f"  {symbol}: {r['error']}")
                continue
            mark = "OK" if r["dir_match"] else "MISS"
            print(
                f"  {symbol}: 실제 {r['actual_now']:,.0f}원({r['actual_change_pct']:+.2f}%)"
                f" vs 모델예측 {r['predicted_price']:,.0f}원({r['predicted_change_pct']:+.2f}%)"
                f"  오차 {r['error_pct']:+.2f}%  방향 {mark}"
            )
        if i < args.n - 1:
            time.sleep(args.interval)

    # 종목별 요약
    print(f"\n{'=' * 60}\n요약 ({args.n}회)\n{'=' * 60}")
    for symbol in SYMBOLS:
        errors = [r[symbol]["error_pct"] for r in all_runs if symbol in r and "error" not in r[symbol]]
        dir_matches = [r[symbol]["dir_match"] for r in all_runs if symbol in r and "error" not in r[symbol]]
        if not errors:
            print(f"{symbol}: 유효한 실행 없음")
            continue
        mae = sum(abs(e) for e in errors) / len(errors)
        bias = sum(errors) / len(errors)  # 부호 유지 평균 -> 시스템적 쏠림 확인
        dir_acc = sum(dir_matches) / len(dir_matches) * 100
        print(
            f"{symbol}: n={len(errors)}  평균절대오차(MAE)={mae:.2f}%  "
            f"평균오차(바이어스)={bias:+.2f}%  방향적중률={dir_acc:.0f}%"
        )
        if abs(bias) > 0.3:
            direction = "과대추정(+)" if bias > 0 else "과소추정(-)"
            print(f"  -> 바이어스가 유의미하게 있어보임 ({direction}). intercept 보정 검토 필요.")


if __name__ == "__main__":
    main()
