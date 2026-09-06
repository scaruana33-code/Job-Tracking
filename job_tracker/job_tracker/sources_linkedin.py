"""
Connector — ingest LinkedIn job-application history.

COMPLIANCE: LinkedIn has NO public API for your own application history, and
scraping violates its ToS. Use the official export:
    Settings & Privacy > Data Privacy > Get a copy of your data > "Job Applications"
Point LINKEDIN_EXPORT at the resulting CSV.
"""
from __future__ import annotations

import hashlib
import logging
import os

import pandas as pd

from .config import LinkedInConfig
from .schema import CANONICAL_COLUMNS

log = logging.getLogger(__name__)


def _hash_id(*parts) -> str:
    return "li:" + hashlib.sha1("|".join(str(p or "") for p in parts).encode()).hexdigest()[:16]


def pull(cfg: LinkedInConfig) -> pd.DataFrame:
    if not os.path.exists(cfg.export_csv):
        log.info("LinkedIn export not found at %s (skipping).", cfg.export_csv)
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    raw = pd.read_csv(cfg.export_csv)
    cols = {c.lower().strip(): c for c in raw.columns}

    def col(*names, default=None):
        for n in names:
            if n in cols:
                return raw[cols[n]]
        return pd.Series([default] * len(raw))

    df = pd.DataFrame(
        {
            "company": col("company name", "company"),
            "role": col("job title", "title"),
            "applied_at": pd.to_datetime(
                col("application date", "date applied", "date"), errors="coerce", utc=True
            ),
            "notes": col("job url", "url", default=""),
        }
    )
    df["application_id"] = [
        _hash_id(c, r, d) for c, r, d in zip(df["company"], df["role"], df["applied_at"])
    ]
    df["source"] = "linkedin"
    df["stage"] = "applied"
    df["stage_level"] = None
    df["offer"] = False
    df["origin"] = "linkedin"

    log.info("LinkedIn export -> %d applications", len(df))
    return df[CANONICAL_COLUMNS]
