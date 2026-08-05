"""반복 실행기.

현재는 단순화를 위해 run_once()가 매 tick마다 모든 소스를 다시 조회한다.
소스별로 실제 캐싱/주기 분리(공매도·수급은 하루 1회 등, docs/PRD.md 6)가
필요해지면 APScheduler job을 소스별로 쪼개고 최신값을 캐시에 저장한 뒤
run_once()가 캐시를 읽도록 리팩터링할 것.

주말에도 SKHYB/SMSN 토큰 신호는 24/7 갱신되므로 별도로 끄지 않는다
(docs/PRD.md 3.1, 6 — 주말 처리).
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from config import INTERVAL_TOKEN_SECONDS
from main import run_once

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main() -> None:
    scheduler = BlockingScheduler()
    scheduler.add_job(run_once, "interval", seconds=INTERVAL_TOKEN_SECONDS, next_run_time=None)
    logger.info("predictor scheduler started (every %ss)", INTERVAL_TOKEN_SECONDS)
    run_once()  # 즉시 1회 실행
    scheduler.start()


if __name__ == "__main__":
    main()
