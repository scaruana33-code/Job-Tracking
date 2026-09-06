"""Connector — pull application data from one or many relational databases."""
from __future__ import annotations

import logging
from typing import List

import pandas as pd
from sqlalchemy import create_engine, text

from .config import DBSource
from .schema import CANONICAL_COLUMNS

log = logging.getLogger(__name__)


def _blank() -> pd.DataFrame:
    return pd.DataFrame(columns=CANONICAL_COLUMNS)


def pull_one(src: DBSource) -> pd.DataFrame:
    try:
        engine = create_engine(src.url)
        with engine.connect() as conn:
            df = pd.read_sql(text(src.query), conn)
    except Exception as exc:  # noqa: BLE001
        log.warning("DB source '%s' failed: %s", src.name, exc)
        return _blank()

    if df.empty:
        return _blank()

    if "source" not in df.columns:
        df["source"] = src.default_source
    df["source"] = df["source"].fillna(src.default_source)
    if "offer" not in df.columns:
        df["offer"] = False
    if "stage" not in df.columns:
        df["stage"] = "applied"
    df["origin"] = f"db:{src.name}"

    for col in CANONICAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df["applied_at"] = pd.to_datetime(df["applied_at"], errors="coerce", utc=True)
    log.info("DB source '%s' -> %d rows", src.name, len(df))
    return df[CANONICAL_COLUMNS]


def pull_all(sources: List[DBSource]) -> pd.DataFrame:
    frames = [pull_one(s) for s in sources]
    return pd.concat(frames, ignore_index=True) if frames else _blank()
