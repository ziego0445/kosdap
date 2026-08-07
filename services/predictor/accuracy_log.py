"""실제 예측 정확도 기록.

predictions.json(gitignore됨, 매 실행마다 덮어씀)과 달리 이 모듈이 쓰는
services/predictor/data/*.json은 **git에 커밋**돼서 GitHub Actions의 매
실행(매번 새 체크아웃)에도 누적된다. 워크플로우가 이 파일들을 커밋해줘야
실제로 쌓인다 (.github/workflows/deploy.yml 참고).

기록 방식: 예측을 만들 때마다 "이번 예측의 기준이 된 종가 날짜"가 지난번
저장해둔 pending estimate의 기준일과 다르면(=그 사이 새 종가가 나왔다는
뜻) pending이 예측했던 값을 이번에 새로 받은 종가(실제값)와 비교해서
accuracy_history에 기록하고, 이번 예측을 새 pending으로 교체한다. 그래서
최소 한 번은 "예측 -> 다음 종가 확정" 사이클이 지나야 기록이 생기기
시작한다 — 서비스를 막 켠 첫날은 당연히 비어있는 게 정상.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent / "data"
_PENDING_PATH = _DATA_DIR / "pending_estimates.json"
_HISTORY_PATH = _DATA_DIR / "accuracy_history.json"


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("%s 읽기 실패 — 기본값으로 시작", path)
        return default


def _save_json(path: Path, data) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def reconcile_and_store(
    symbol: str,
    trade_date: str,
    last_close: float,
    predicted_price: float,
    change_percent: float,
) -> None:
    pending: dict = _load_json(_PENDING_PATH, {})
    history: list = _load_json(_HISTORY_PATH, [])

    prior = pending.get(symbol)
    if prior and prior.get("based_on_date") != trade_date and last_close:
        predicted = prior["predicted_price"]
        base_price = prior.get("based_on_price")
        error_pct = (predicted - last_close) / last_close * 100
        actual_change_pct = (
            (last_close - base_price) / base_price * 100 if base_price else None
        )
        history.append(
            {
                "symbol": symbol,
                "date": trade_date,
                "predicted_price": predicted,
                "actual_price": last_close,
                "error_percent": round(error_pct, 2),
                "predicted_change_percent": prior.get("change_percent"),
                "actual_change_percent": round(actual_change_pct, 2) if actual_change_pct is not None else None,
                "predicted_at": prior.get("predicted_at"),
                "recorded_at": dt.datetime.now(dt.UTC).isoformat(),
            }
        )
        _save_json(_HISTORY_PATH, history)
        logger.info("%s: %s 예측 정확도 기록됨 (오차 %.2f%%)", symbol, trade_date, error_pct)

    pending[symbol] = {
        "based_on_date": trade_date,
        "based_on_price": last_close,
        "predicted_price": predicted_price,
        "change_percent": change_percent,
        "predicted_at": dt.datetime.now(dt.UTC).isoformat(),
    }
    _save_json(_PENDING_PATH, pending)


def compute_recent_accuracy_percent(symbol: str, lookback: int = 30) -> float | None:
    """최근 기록의 방향(상승/하락) 적중률(%). 기록이 없으면 None — 호출부가
    적당한 폴백(예: 백테스트 추정치)을 쓰도록 구분해서 알려준다."""
    history = _load_json(_HISTORY_PATH, [])
    records = [r for r in history if r.get("symbol") == symbol][-lookback:]
    scoreable = [
        r for r in records
        if r.get("predicted_change_percent") is not None and r.get("actual_change_percent") is not None
    ]
    if not scoreable:
        return None
    hits = sum(
        1 for r in scoreable
        if (r["predicted_change_percent"] >= 0) == (r["actual_change_percent"] >= 0)
    )
    return round(hits / len(scoreable) * 100, 1)


def export_history_for_web(dest: Path) -> None:
    """apps/web/public/accuracy-history.json으로 복사 — predictions.json과
    같은 방식(정적 export가 읽는 브리지). 이 파일 자체는 gitignore돼도 됨,
    원본(data/accuracy_history.json)만 커밋되면 매 빌드 때 재생성 가능."""
    history = _load_json(_HISTORY_PATH, [])
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.exception("정확도 기록 웹 내보내기 실패 (%s)", dest)
