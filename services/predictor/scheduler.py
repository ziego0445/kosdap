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
import os
import sys
from pathlib import Path

import time

# 콘솔 코드페이지(cp949)에서 한글 로그가 깨지지 않도록 UTF-8로 강제.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001 - 콘솔이 없는 환경(파이프 등)에서는 무시
        pass

# 2026-08-17 실측: run_scheduler.bat을 실제 콘솔 창에서 띄운 상태로 몇
# 사이클 도는 걸 확인했는데(네트워크 정상, 서브프로세스 정상 종료,
# predictions.json도 갱신됨), 그 다음부턴 CPU 0%로 몇십 분씩 완전히
# 멈췄다 — 매번 "성공적으로 몇 사이클 돌다가 어느 순간부터 영원히
# 멈춤" 패턴이 반복돼서 코드 버그로 계속 오인했었는데, 실은 Windows
# 콘솔의 "빠른 편집 모드(QuickEdit Mode)" 때문일 가능성이 높다 — 콘솔
# 창 안을 클릭/드래그해서 텍스트를 선택하면(의도치 않은 스크롤 포함)
# Windows가 그 창에 쓰려는 프로세스를 Esc를 누르기 전까지 통째로
# 멈춰버린다. logging의 StreamHandler(sys.stdout) 쓰기가 이 창을
# 거치므로, 한 번 걸리면 같은 emit() 안의 FileHandler까지 같이 멈춰서
# 로그 파일도 함께 끊긴다 — 여기서 프로그램적으로 꺼서 이 문제 자체를
# 없앤다. 콘솔이 없는 환경(파이프/서비스로 실행 등)에서는 조용히 무시.
if sys.platform == "win32":
    try:
        import ctypes

        _STD_INPUT_HANDLE = -10
        _ENABLE_EXTENDED_FLAGS = 0x0080
        _ENABLE_QUICK_EDIT_MODE = 0x0040
        _kernel32 = ctypes.windll.kernel32
        _console_handle = _kernel32.GetStdHandle(_STD_INPUT_HANDLE)
        _mode = ctypes.c_uint32()
        if _console_handle and _kernel32.GetConsoleMode(_console_handle, ctypes.byref(_mode)):
            _new_mode = (_mode.value & ~_ENABLE_QUICK_EDIT_MODE) | _ENABLE_EXTENDED_FLAGS
            _kernel32.SetConsoleMode(_console_handle, _new_mode)
    except Exception:  # noqa: BLE001
        pass

_LOG_DIR = Path(__file__).resolve().parent / "logs"
_LOG_DIR.mkdir(exist_ok=True)
_LOG_FILE = _LOG_DIR / "scheduler.log"

# 콘솔(눈으로 보기)과 파일(logs/scheduler.log, 나중에 다시 확인하기) 둘 다에 남긴다 —
# 창을 숨겨서(작업 스케줄러) 돌려도 파일 로그는 계속 쌓이도록.
# main.py도 자체적으로 logging.basicConfig()를 호출하는데, basicConfig()는 root
# logger에 핸들러가 이미 있으면 아무것도 안 하므로(no-op) — 여기서 먼저 설정해서
# main import 시점의 basicConfig 호출이 이 설정을 덮어쓰지 못하게 import보다 앞에 둔다.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(_LOG_FILE, encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

import concurrent.futures
import subprocess

import git_sync
from config import INTERVAL_TOKEN_SECONDS

_PREDICTOR_DIR = Path(__file__).resolve().parent
_SYNC_INTERVAL_SECONDS = 900  # 15분마다 — GitHub Actions 봇 커밋과 너무 자주
# 부딪히지 않으면서도(git_sync.py의 재시도 로직이 있긴 함), CI가 읽는
# token_change_cache.json이 크게 오래되지 않도록(캐시 유효기간 30분) 하는 절충.

# 2026-08-16 실측: yfinance(_util.py의 pct_change)가 requests/curl_cffi 레벨
# timeout=10s를 갖고 있는데도, 네트워크가 특정 방식으로 막히면(연결은 열렸는데
# 응답이 영영 안 오는 등) 이 timeout이 안 먹고 무한정 멈추는 걸 확인함 — 게다가
# 처음엔 "run_once를 스레드+ThreadPoolExecutor 타임아웃으로 감싸면 되겠지" 하고
# 고쳤는데도 다시 멈췄다: curl_cffi가 막힌 동안 GIL을 안 놔줘서 워치독 스레드
# 자체가 못 깨어남(CPU 사용량이 5분 넘게 그대로였음 — 실측 확인). 스레드로는
# 원천적으로 못 끊는 부류의 멈춤이라, run_once는 아예 `python main.py`를
# 서브프로세스로 실행하고 타임아웃 걸리면 OS 레벨에서 kill한다 — 이건 GIL과
# 무관하게 확실히 끊긴다(GitHub Actions도 어차피 `python main.py`로 매번 새
# 프로세스를 띄우는 방식이라 여기서도 그 진입점을 그대로 재사용).
_RUN_ONCE_TIMEOUT_SECONDS = 150


def _run_main_once() -> None:
    # main.py는 자체 sys.stdout 인코딩을 안 건드리므로(시스템 기본 cp949로 출력)
    # 여기서 UTF-8로 디코딩하면 한글이 깨진다 — 자식 프로세스 자체를 UTF-8
    # 출력 모드로 강제해서 부모의 utf-8 디코딩과 맞춘다.
    child_env = os.environ.copy()
    child_env["PYTHONIOENCODING"] = "utf-8"
    try:
        result = subprocess.run(
            [sys.executable, "main.py"],
            cwd=_PREDICTOR_DIR,
            timeout=_RUN_ONCE_TIMEOUT_SECONDS,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=child_env,
        )
    except subprocess.TimeoutExpired:
        logger.error(
            "main.py가 %d초 안에 끝나지 않아 강제 종료하고 이번 사이클은 건너뜁니다 "
            "(네트워크 호출이 멈췄을 가능성 — 다음 사이클에 자동 재시도)",
            _RUN_ONCE_TIMEOUT_SECONDS,
        )
        return
    except Exception:
        logger.exception("main.py 서브프로세스 실행 중 예외 발생")
        return

    for line in (result.stdout or "").splitlines():
        logger.info("[main.py] %s", line)
    for line in (result.stderr or "").splitlines():
        logger.warning("[main.py stderr] %s", line)
    if result.returncode != 0:
        logger.error("main.py 비정상 종료 (exit code %d)", result.returncode)


# git_sync.sync는 `git` 서브프로세스만 호출해서(subprocess.run은 대기 중 GIL을
# 놔주므로) 스레드 타임아웃으로도 안전하게 끊긴다 — run_once와 달리 굳이 별도
# 프로세스로 뺄 필요는 없다.
_WATCHDOG_POOL = concurrent.futures.ThreadPoolExecutor(
    max_workers=2, thread_name_prefix="watchdog"
)


def _run_with_timeout(func, timeout_seconds: float, name: str) -> None:
    future = _WATCHDOG_POOL.submit(func)
    try:
        future.result(timeout=timeout_seconds)
    except concurrent.futures.TimeoutError:
        logger.error(
            "%s가 %.0f초 안에 끝나지 않아 이번 사이클은 건너뜁니다 "
            "(다음 사이클에 자동 재시도)",
            name, timeout_seconds,
        )
    except Exception:
        logger.exception("%s 실행 중 예외 발생", name)


def main() -> None:
    # 2026-08-17 실측: APScheduler(BlockingScheduler)로 반복시켰더니 맨 처음
    # 즉시 1회(_run_main_once() 직접 호출)는 항상 성공하는데, scheduler.start()
    # 이후의 "5분마다 자동 반복" 트리거가 이 환경에서 단 한 번도 실제로 발동한
    # 적이 없었다(17시간 동안 CPU 0.36초, 로그 0줄 — 네트워크가 멈춘 것도
    # 아니고 그냥 아무 것도 안 함). 원인을 못 찾아서, 검증할 내부 동작이 없는
    # 제일 단순한 방식(수동 while 루프 + time.sleep)으로 대체한다.
    logger.info(
        "predictor scheduler started (every %ss, git sync every %ss)",
        INTERVAL_TOKEN_SECONDS, _SYNC_INTERVAL_SECONDS,
    )
    last_sync = 0.0
    while True:
        cycle_start = time.monotonic()
        _run_main_once()
        if cycle_start - last_sync >= _SYNC_INTERVAL_SECONDS:
            _run_with_timeout(git_sync.sync, 60, "git_sync.sync")
            last_sync = cycle_start
        elapsed = time.monotonic() - cycle_start
        sleep_for = max(0.0, INTERVAL_TOKEN_SECONDS - elapsed)
        logger.info("다음 사이클까지 %.0f초 대기", sleep_for)
        time.sleep(sleep_for)


if __name__ == "__main__":
    main()
