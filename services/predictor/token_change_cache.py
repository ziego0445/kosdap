"""Bybit token_change_percent 로컬→CI 폴백 캐시.

GitHub Actions(클라우드 IP)에서는 Bybit API가 구조적으로 403 차단된다
(2026-08-08 실측 확인 — CloudFront가 AWS/Azure/GCP 데이터센터 IP 대역을
지역과 무관하게 차단하고 있고, api.bytick.com 미러도 동일하게 막힘. EU
전용 도메인(api.bybit.eu)엔 이 토큰화 상품 자체가 없고, 테스트넷은 가짜
데이터라 못 씀 — collectors/tokenized.py 참고). 로컬(한국 IP)에서는 문제
없이 동작하므로, 로컬이 성공적으로 계산한 token_change_percent를 git에
커밋되는 이 파일에 저장해두고, CI에서 직접 조회가 실패하면 신선도 내인
경우에 한해 이 캐시로 대체한다.

캐시를 실제로 최신 상태로 유지하려면 로컬 scheduler.py가 주기적으로 이
파일을 git commit+push까지 해줘야 한다 (git_sync.py 참고) — 그냥 로컬
디스크에만 있으면 GitHub Actions가 체크아웃할 때 못 본다.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CACHE_PATH = Path(__file__).resolve().parent / "data" / "token_change_cache.json"
_MAX_AGE_SECONDS = 1800  # 30분 — 로컬이 최소 10~15분마다는 갱신해준다는 전제


def _load_all() -> dict:
    if not _CACHE_PATH.exists():
        return {}
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("%s 읽기 실패", _CACHE_PATH)
        return {}


def save(symbol: str, token_change_percent: float) -> None:
    """Bybit 직접 조회가 성공했을 때(=대부분 로컬) 호출해서 캐시를 갱신한다."""
    try:
        data = _load_all()
        data[symbol] = {
            "token_change_percent": token_change_percent,
            "updated_at": dt.datetime.now(dt.UTC).isoformat(),
        }
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.exception("token_change_cache 저장 실패 (%s)", symbol)


def load_fresh(symbol: str) -> float | None:
    """직접 조회가 실패했을 때(=대부분 CI) 호출한다. 캐시가 없거나 너무
    오래됐으면 None — 오래된 값을 실제 값인 것처럼 쓰면 안 되므로."""
    try:
        entry = _load_all().get(symbol)
        if not entry:
            return None
        updated_at = dt.datetime.fromisoformat(entry["updated_at"])
        age_seconds = (dt.datetime.now(dt.UTC) - updated_at).total_seconds()
        if age_seconds > _MAX_AGE_SECONDS:
            logger.warning(
                "%s: token_change 캐시가 %.0f분 전 값이라 너무 오래됨 — 사용 안 함",
                symbol, age_seconds / 60,
            )
            return None
        return entry["token_change_percent"]
    except Exception:
        logger.exception("token_change_cache 읽기 실패 (%s)", symbol)
        return None
