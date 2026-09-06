"""
Orchestrator: pull -> normalize -> persist -> write-back to Excel -> email digest.

`run_pipeline()` is the single function the CLI, scheduler, and dashboard button
all call.
"""
from __future__ import annotations

import logging
import os

import pandas as pd
from sqlalchemy import create_engine

from . import sources_db, sources_excel, sources_gmail, sources_linkedin
from .config import CONFIG, AppConfig
from .normalize import normalize

log = logging.getLogger(__name__)


def _ensure_data_dir(url: str) -> None:
    if url.startswith("sqlite:///"):
        path = url.replace("sqlite:///", "")
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)


def collect_raw(cfg: AppConfig) -> pd.DataFrame:
    """Pull from every configured connector and union the results."""
    frames = [
        sources_excel.pull(cfg.excel.path),      # your tracker rows
        sources_db.pull_all(cfg.db_sources),     # relational DBs
        sources_gmail.pull(cfg.gmail),           # Gmail events
        sources_linkedin.pull(cfg.linkedin),     # LinkedIn export
    ]
    frames = [f for f in frames if f is not None and not f.empty]
    if not frames:
        log.warning("No data returned from any source.")
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def persist(df: pd.DataFrame, warehouse_url: str) -> None:
    _ensure_data_dir(warehouse_url)
    engine = create_engine(warehouse_url)
    df.to_sql("applications_fact", engine, if_exists="replace", index=False)
    log.info("Persisted %d applications to %s", len(df), warehouse_url)


def load_fact(warehouse_url: str) -> pd.DataFrame:
    engine = create_engine(warehouse_url)
    try:
        df = pd.read_sql("SELECT * FROM applications_fact", engine)
        df["applied_at"] = pd.to_datetime(df["applied_at"], errors="coerce", utc=True)
        df["week"] = pd.to_datetime(df["week"], errors="coerce")
        return df
    except Exception:  # noqa: BLE001
        return pd.DataFrame()


def run_pipeline(cfg: AppConfig = CONFIG, send_email: bool = True) -> pd.DataFrame:
    log.info("=== Job-tracker pipeline run start ===")
    raw = collect_raw(cfg)
    fact = normalize(raw)
    persist(fact, cfg.warehouse_url)

    # Write results back into the Excel tracker (fills Applications, recomputes
    # Dashboard + Source Analysis tabs)
    if cfg.excel.write_back and not fact.empty:
        try:
            sources_excel.write_back(fact, cfg.excel.path)
        except Exception as exc:  # noqa: BLE001
            log.warning("Excel write-back failed: %s", exc)

    if send_email and not fact.empty:
        from .report import build_digest_html

        html, subject = build_digest_html(fact)
        sources_gmail.send_digest(cfg.gmail, html, subject)

    log.info("=== Job-tracker pipeline run complete (%d apps) ===", len(fact))
    return fact
