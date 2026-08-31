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


def _spans_weekend(old_date_str: str | None, new_date_str: str) -> bool:
    """`old_date`와 `new_date` 사이(둘 다 제외)에 토요일/일요일이 하루라도
    끼어있으면 True — "주말 동안(장 닫힌 상태로) 계속 갱신되던 예측이 다음
    개장일 실제 종가로 확정됐다"는 뜻이다. 날짜 파싱 실패 시 안전하게 False."""
    if not old_date_str:
        return False
    try:
        old_d = dt.date.fromisoformat(old_date_str)
        new_d = dt.date.fromisoformat(new_date_str)
    except (ValueError, TypeError):
        return False
    d = old_d + dt.timedelta(days=1)
    while d < new_d:
        if d.weekday() >= 5:  # 5=토, 6=일
            return True
        d += dt.timedelta(days=1)
    return False


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
        # 2026-08-30 실측으로 발견한 버그: 로컬 스케줄러와 GitHub Actions가
        # 서로 독립적으로 같은 파이프라인(main.py)을 돌리면서 각자
        # pending_estimates.json을 갱신하고 git으로 동기화하다 보니, 어느
        # 한쪽의 병합 시점에 pending이 "리셋"된 것처럼 보여 같은
        # (symbol, date) 조합이 서로 다른 값으로 두 번 기록되는 사고가
        # 있었다. 기록 전에 이미 있는지 확인해서 중복 적재를 막는다 —
        # 근본 원인(로컬/CI 이중 기록)은 그대로지만, 최소한 정확도 통계가
        # 이중 계산되는 건 막는다.
        already_recorded = any(
            r.get("symbol") == symbol and r.get("date") == trade_date for r in history
        )
        if already_recorded:
            logger.warning(
                "%s: %s 예측 정확도가 이미 기록돼 있어 중복 기록을 건너뜀 "
                "(로컬/CI 동시 실행으로 pending이 리셋됐을 가능성)",
                symbol, trade_date,
            )
        else:
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
                    # 이 예측이 주말(토/일)을 건너뛰고 확정됐는지 — "주말에
                    # 만든 예측이 월요일 개장 때 얼마나 맞았는지" 필터링용
                    # (compute_weekend_accuracy_percent 참고).
                    "spannedWeekend": _spans_weekend(prior.get("based_on_date"), trade_date),
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


def compute_weekend_accuracy_percent(symbol: str, lookback: int = 30) -> float | None:
    """주말(토/일)을 건너뛴 예측만 골라 방향(상승/하락) 적중률(%) —
    compute_recent_accuracy_percent와 계산 방식은 같지만 spannedWeekend=True인
    기록만 대상으로 한다. 기록이 없으면 None."""
    history = _load_json(_HISTORY_PATH, [])
    records = [
        r for r in history
        if r.get("symbol") == symbol and r.get("spannedWeekend")
    ][-lookback:]
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
