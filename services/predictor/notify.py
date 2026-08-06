"""텔레그램 관리자 장애 알림.

데이터 수집/파이프라인 에러를 admin_logs(Supabase)뿐 아니라 텔레그램으로도
바로 받기 위함. python-telegram-bot 같은 무거운 의존성 대신 Bot HTTP API를
requests로 직접 호출한다 (요구되는 기능은 sendMessage 하나뿐이라 충분함).

키 출처: c:\\ziegoProject\\bitcoinalert\\server.py (2026-08-06, 사용자 요청으로 이관)
"""

from __future__ import annotations

import logging

import requests

from config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


def send_telegram_message(text: str) -> bool:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("TELEGRAM_BOT_TOKEN/CHAT_ID 미설정 — 알림 건너뜀: %s", text)
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": text},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception:
        logger.exception("텔레그램 알림 전송 실패")
        return False


def notify_pipeline_error(source: str, detail: str) -> None:
    send_telegram_message(f"⚠️ kosdap 파이프라인 오류\n소스: {source}\n내용: {detail}")
