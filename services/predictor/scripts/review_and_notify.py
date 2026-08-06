"""세션 전환마다 도는 /loop 리뷰 체크포인트: 파이프라인을 한 번 돌리고,
결과 요약을 텔레그램으로 보낸다.

에러 알림(notify.notify_pipeline_error)과는 별개 — 이건 "정상 동작 중"인
정기 리뷰 결과를 보여주는 용도. main.py의 5분 주기 scheduler는 매번 이걸
보내면 스팸이 되니, 세션 전환 시점에만 도는 이 스크립트에서만 쓴다.

사용:
    python scripts/review_and_notify.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")

import datetime as dt
import json

from collectors.market_hours import KST, get_session
from config import SYMBOLS
from main import run_once, _WEB_SNAPSHOT_PATH
from notify import send_telegram_message

SESSION_LABEL = {
    "open": "정규장 운영 중",
    "pre_market": "장전 시간외",
    "post_market": "장후 시간외",
    "closed": "휴장",
}


def build_summary() -> str:
    session = get_session()
    now = dt.datetime.now(KST).strftime("%Y-%m-%d %H:%M KST")
    lines = [f"kosdap 세션 리뷰 — {now}", f"세션: {SESSION_LABEL.get(session, session)}", ""]

    if not _WEB_SNAPSHOT_PATH.exists():
        lines.append("predictions.json 없음 — 파이프라인 실행 실패 가능성")
        return "\n".join(lines)

    rows = json.loads(_WEB_SNAPSHOT_PATH.read_text(encoding="utf-8"))
    by_symbol = {r["symbol"]: r for r in rows}

    for symbol, meta in SYMBOLS.items():
        r = by_symbol.get(symbol)
        if not r:
            lines.append(f"{meta['name']}: 데이터 없음")
            continue
        current = int(round(r["currentPrice"]))
        if r["isEstimate"]:
            predicted = int(round(r["predictedPrice"]))
            lines.append(
                f"{meta['name']}: {current:,}원 -> 추정 {predicted:,}원 "
                f"({r['changePercent']:+.2f}%) 신뢰도 {r['confidence']:.0f}%"
            )
        else:
            lines.append(
                f"{meta['name']}: 실시간가 {current:,}원 (전일比 {r['changePercent']:+.2f}%)"
            )

    return "\n".join(lines)


def main() -> None:
    run_once()
    summary = build_summary()
    print(summary)
    ok = send_telegram_message(summary)
    print(f"\n텔레그램 전송: {'성공' if ok else '실패'}")


if __name__ == "__main__":
    main()
