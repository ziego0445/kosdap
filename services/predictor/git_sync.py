"""로컬 scheduler.py가 주기적으로 호출하는 git 동기화.

services/predictor/data/ 아래 파일(정확도 기록, 플로우 가드 상태, 토큰가
캐시 등)을 git에 커밋+푸시해서 GitHub Actions가 최신 값을 읽을 수 있게
한다 — 특히 token_change_cache.json은 로컬(한국 IP)만 Bybit에 접근 가능해
CI가 이걸 못 올리면 24/7 핵심 신호가 CI 배포판에서 계속 빠지게 된다
(token_change_cache.py 참고).

GitHub Actions도 같은 디렉터리에 독립적으로 커밋한다(정확도 기록 갱신,
.github/workflows/deploy.yml). 두 프로세스가 비슷한 시각에 push하면
non-fast-forward로 거절될 수 있어 pull --rebase 후 재시도한다.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DATA_DIR = "services/predictor/data"
_MAX_PUSH_ATTEMPTS = 3


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=_REPO_ROOT, capture_output=True, text=True, timeout=30
    )


def sync() -> None:
    """변경사항이 있으면 커밋하고, push 실패 시 pull --rebase 후 재시도한다.
    실패해도 예외를 올리지 않는다 — 다음 주기에 다시 시도하면 되니까 스케줄러
    전체를 죽일 이유가 없다."""
    try:
        _run("add", _DATA_DIR)
        status = _run("status", "--porcelain", "--", _DATA_DIR)
        if not status.stdout.strip():
            return  # 변경 없음

        # [skip ci]: 이 push 자체가 GitHub Actions의 push 트리거를 다시
        # 돌리지 않도록(불필요한 중복 배포 방지) — 기존 봇 커밋과 동일 컨벤션.
        commit = _run("commit", "-m", "chore: 로컬 데이터 캐시 동기화 [skip ci]")
        if commit.returncode != 0:
            logger.warning("git commit 실패 — 다음 주기에 재시도: %s", commit.stderr.strip())
            return

        for attempt in range(1, _MAX_PUSH_ATTEMPTS + 1):
            push = _run("push")
            if push.returncode == 0:
                logger.info("로컬 데이터 캐시 push 완료")
                return
            logger.warning(
                "git push 실패(시도 %d/%d) — pull --rebase 후 재시도: %s",
                attempt, _MAX_PUSH_ATTEMPTS, push.stderr.strip(),
            )
            rebase = _run("pull", "--rebase")
            if rebase.returncode != 0:
                logger.error("git pull --rebase 실패 — 동기화 포기, 다음 주기에 재시도: %s", rebase.stderr.strip())
                return
        logger.error("git push %d회 재시도 모두 실패 — 다음 주기에 다시 시도", _MAX_PUSH_ATTEMPTS)
    except Exception:
        logger.exception("로컬 데이터 캐시 동기화 실패")
