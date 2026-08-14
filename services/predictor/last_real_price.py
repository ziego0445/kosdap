"""정규장/시간외에서 확보한 실제 체결가를 로컬(→git→CI)에 캐싱.

closed 세션(장마감 후 저녁·주말)에 화면에 보여줄 "현재가"를 더 신선하게
만드는 용도. 2026-08-14 실측으로 발견한 문제: 16:00~18:00 장후 시간외에서
이미 실제 체결가를 확보해놓고도, 18:00을 넘어 closed 세션으로 넘어가면
그 값을 버리고 15:30 정규장 종가로 되돌아가 "현재가"라고 표시하고 있었다.

주의: 예측 계산 자체(모델의 last_close 기준 score 산출)는 학습 방식
(정규장 종가→다음 정규장 종가)과 어긋나지 않도록 그대로 last_close를
쓴다. 이 캐시는 오직 "사용자에게 보여줄 현재가/변동률" 표시값만 더
신선하게 바꾸는 용도로만 쓴다 — 모델 입력에 섞으면 이미 반영된 움직임을
또 더하는 이중 반영이 된다.

토큰가 캐시(token_change_cache.py)와 같은 이유로 git에 커밋돼야 CI(매번
새 프로세스로 뜨는 GitHub Actions)에서도 보인다.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_CACHE_PATH = Path(__file__).resolve().parent / "data" / "last_real_price.json"


def _load_all() -> dict:
    if not _CACHE_PATH.exists():
        return {}
    try:
        return json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        logger.exception("%s 읽기 실패", _CACHE_PATH)
        return {}


def save(symbol: str, price: float, session: str, trade_date: str) -> None:
    """실제가(정규장/시간외)를 성공적으로 조회했을 때마다 호출."""
    try:
        data = _load_all()
        data[symbol] = {
            "price": price,
            "session": session,
            "trade_date": trade_date,
            "captured_at": dt.datetime.now(dt.UTC).isoformat(),
        }
        _CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        _CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        logger.exception("last_real_price 저장 실패 (%s)", symbol)


def load_post_market_anchor(symbol: str, trade_date: str) -> float | None:
    """`trade_date`(모델이 예측 기준으로 쓰는 정규장 종가일)와 같은 날
    장후 시간외(post_market)에서 확보한 실제가만 돌려준다.

    session이 post_market이 아니거나 날짜가 다르면 None. 두 조건 다
    인과관계 때문에 필요하다: pre_market은 그날 개장 "전" 데이터라 당일
    종가보다 최신이라고 볼 수 없고, 날짜가 다르면 다른 거래일의 낡은
    캐시일 수 있다(예: 오늘 장후 시간외 수집이 실패해 캐시가 그제 값에
    머물러 있는 경우) — 그런 값을 최신인 것처럼 보여주면 안 되므로 조용히
    None을 돌려주고 호출부가 last_close로 폴백하게 한다.
    """
    entry = _load_all().get(symbol)
    if not entry:
        return None
    if entry.get("session") != "post_market" or entry.get("trade_date") != trade_date:
        return None
    return entry.get("price")
