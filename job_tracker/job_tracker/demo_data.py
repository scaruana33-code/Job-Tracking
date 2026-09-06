"""
Synthetic data generator so you can see the whole thing working without wiring
real credentials.  `python -m job_tracker.cli demo`
"""
from __future__ import annotations

import random

import numpy as np
import pandas as pd

from .classify import stage_level

random.seed(7)
np.random.seed(7)

_COMPANIES = [
    "Anthropic", "Amazon", "Stripe", "Databricks", "Notion", "Ramp", "Figma",
    "Snowflake", "Airbnb", "Datadog", "Plaid", "Brex", "Rippling", "Retool",
    "Vanta", "Scale AI", "OpenAI", "Coinbase", "Instacart", "DoorDash",
]
_ROLES = [
    "Program Manager", "Sr. Program Manager", "TPM", "Operations Manager",
    "Product Operations", "Workforce Program Lead", "Vendor Program Manager",
]
_SOURCE_PROFILE = {
    "recruiter": (0.55, 0.22),
    "networking": (0.48, 0.20),
    "linkedin": (0.14, 0.10),
    "ats": (0.11, 0.08),
}


def _sample_stage(source: str) -> str:
    p_iv, p_off = _SOURCE_PROFILE.get(source, (0.12, 0.08))
    if random.random() > p_iv:
        return "rejected" if random.random() < 0.6 else "applied"
    ladder = ["phone_1", "interview_2", "interview_3", "onsite_final"]
    stage = "phone_1"
    for nxt in ladder[1:]:
        if random.random() < 0.55:
            stage = nxt
        else:
            break
    if stage == "onsite_final" and random.random() < p_off + 0.25:
        return "offer"
    return stage


def make_demo_fact(n: int = 140, weeks_back: int = 16) -> pd.DataFrame:
    now = pd.Timestamp.utcnow().normalize()
    rows = []
    for i in range(n):
        source = random.choices(
            ["ats", "linkedin", "networking", "recruiter"], weights=[0.42, 0.33, 0.15, 0.10]
        )[0]
        wk = random.randint(0, weeks_back - 1)
        applied = now - pd.Timedelta(weeks=wk, days=random.randint(0, 6))
        applied = applied.tz_localize("UTC") if applied.tz is None else applied
        stage = _sample_stage(source)
        rows.append(
            {
                "application_id": f"demo:{i}",
                "company": random.choice(_COMPANIES),
                "role": random.choice(_ROLES),
                "applied_at": applied,
                "source": source,
                "stage": stage,
                "stage_level": stage_level(stage),
                "offer": stage == "offer",
                "origin": "demo",
                "notes": "",
            }
        )
    df = pd.DataFrame(rows)
    df["week"] = (
        df["applied_at"].dt.tz_convert("UTC").dt.tz_localize(None)
        .dt.to_period("W-SUN").dt.start_time
    )
    return df
