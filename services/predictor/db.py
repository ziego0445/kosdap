"""Supabase client wrapper. Uses the service-role key (write access) —
never expose this key to the web app; the web app reads with the anon key.
"""

from __future__ import annotations

import logging
from typing import Any

from supabase import Client, create_client

from config import SUPABASE_SERVICE_ROLE_KEY, SUPABASE_URL

logger = logging.getLogger(__name__)

_client: Client | None = None


def get_client() -> Client | None:
    global _client
    if _client is not None:
        return _client
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        logger.warning("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY not set — DB writes are no-ops")
        return None
    _client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
    return _client


def insert(table: str, row: dict[str, Any]) -> None:
    client = get_client()
    if client is None:
        logger.info("[dry-run] insert into %s: %s", table, row)
        return
    client.table(table).insert(row).execute()


def log_admin_event(source: str, status: str, detail: str = "") -> None:
    insert(
        "admin_logs",
        {"source": source, "status": status, "detail": detail},
    )
