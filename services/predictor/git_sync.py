"""로컬 scheduler.py가 주기적으로 호출하는 git 동기화.

services/predictor/data/ 아래 파일(정확도 기록, 플로우 가드 상태, 토큰가
캐시 등)을 git에 커밋+푸시해서 GitHub Actions가 최신 값을 읽을 수 있게
한다 — 특히 token_change_cache.json은 로컬(한국 IP)만 Bybit에 접근 가능해
CI가 이걸 못 올리면 24/7 핵심 신호가 CI 배포판에서 계속 빠지게 된다
(token_change_cache.py 참고).

GitHub Actions도 같은 디렉터리에 독립적으로 커밋한다(정확도 기록 갱신,
.github/workflows/deploy.yml). 두 프로세스가 비슷한 시각에 push하면
non-fast-forward로 거절될 수 있다.

2026-08-17 실측: 원래는 push 실패 시 `git pull --rebase`로 재시도했는데,
data/*.json이 자주 같은 줄에서 충돌하는 성격이라(둘 다 "최신 스냅샷"을
같은 키에 덮어쓰는 캐시 파일) 리베이스 도중 충돌이 나면 detached HEAD +
conflict-marker 상태로 멈춰버렸다 — 다음 사이클에 main.py가 그 충돌
마커가 그대로 남은 파일을 읽다가 JSONDecodeError를 내는 사고까지 발생.
리베이스는 사람이 수동으로 계속(rebase --continue)해야 완전히 풀리는
구조라 자동 재시도와는 원래 안 맞았다. `git merge -X ours`로 교체 —
merge는 실패해도 현재 브랜치에 그대로 남아있고(detached HEAD 없음),
`-X ours`가 텍스트 충돌을 사람 개입 없이 "이번에 로컬이 만든 값"으로
자동 해소한다(어차피 다음 사이클에 다시 덮어써질 캐시라 어느 쪽이
이기든 상관없음 — 매번 로컬이 이기게 고정해서 예측 가능하게 함).
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
        ["git", *args], cwd=_REPO_ROOT, capture_output=True, text=True, timeout=30,
        encoding="utf-8", errors="replace",
    )


def sync() -> None:
    """변경사항이 있으면 커밋하고, push 실패 시 merge -X ours 후 재시도한다.
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
                "git push 실패(시도 %d/%d) — fetch + merge -X ours 후 재시도: %s",
                attempt, _MAX_PUSH_ATTEMPTS, push.stderr.strip(),
            )
            fetch = _run("fetch", "origin", "master")
            if fetch.returncode != 0:
                logger.error("git fetch 실패 — 동기화 포기, 다음 주기에 재시도: %s", fetch.stderr.strip())
                return
            merge = _run("merge", "-X", "ours", "--no-edit", "origin/master")
            if merge.returncode != 0:
                logger.error(
                    "git merge 실패 — merge 중단하고 동기화 포기, 다음 주기에 재시도: %s",
                    merge.stderr.strip(),
                )
                _run("merge", "--abort")
                return
        logger.error("git push %d회 재시도 모두 실패 — 다음 주기에 다시 시도", _MAX_PUSH_ATTEMPTS)
    except Exception:
        logger.exception("로컬 데이터 캐시 동기화 실패")
