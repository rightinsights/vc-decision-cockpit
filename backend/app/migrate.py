"""
Tiny forward-only schema catch-up for deployments that predate a column. create_all never alters
existing tables, so each added column is listed here with its DDL and applied if missing.
"""

from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

log = logging.getLogger("migrate")

# (table, column, DDL type/default). Keep entries forever; they are idempotent.
ADDED_COLUMNS: list[tuple[str, str, str]] = [
    ("documents", "ocr_pages", "INTEGER NOT NULL DEFAULT 0"),
]


def ensure_columns(engine: Engine) -> list[str]:
    inspector = inspect(engine)
    applied: list[str] = []
    with engine.begin() as conn:
        for table, column, ddl in ADDED_COLUMNS:
            if table not in inspector.get_table_names():
                continue
            existing = {c["name"] for c in inspector.get_columns(table)}
            if column in existing:
                continue
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))
            applied.append(f"{table}.{column}")
            log.info("added column %s.%s", table, column)
    return applied
