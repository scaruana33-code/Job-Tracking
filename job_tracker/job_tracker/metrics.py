"""Weekly metrics + funnel-by-source rollups."""
from __future__ import annotations

import pandas as pd

from .schema import STAGE_LABELS, STAGE_ORDER

_INTERVIEW_STAGES = ["phone_1", "interview_2", "interview_3", "onsite_final", "offer"]
_ROUND_STAGES = ["phone_1", "interview_2", "interview_3", "onsite_final"]


def _reached(df: pd.DataFrame, stage: str) -> pd.Series:
    return df["stage_level"] >= STAGE_ORDER[stage]


def weekly_applications(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    g = df.groupby(["week", "source"]).size().reset_index(name="applications")
    return g.pivot(index="week", columns="source", values="applications").fillna(0).astype(int)


def weekly_interviews_by_level(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for stage in _ROUND_STAGES + ["offer"]:
        for week, n in df[_reached(df, stage)].groupby("week").size().items():
            rows.append({"week": week, "stage": STAGE_LABELS[stage], "count": int(n)})
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    return out.pivot(index="week", columns="stage", values="count").fillna(0).astype(int)


def weekly_interviews_by_source(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    iv = df[df["stage"].isin(_INTERVIEW_STAGES)]
    if iv.empty:
        return pd.DataFrame()
    g = iv.groupby(["week", "source"]).size().reset_index(name="interviews")
    return g.pivot(index="week", columns="source", values="interviews").fillna(0).astype(int)


def weekly_offers(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    off = df[df["offer"]]
    if off.empty:
        return pd.DataFrame()
    g = off.groupby(["week", "source"]).size().reset_index(name="offers")
    return g.pivot(index="week", columns="source", values="offers").fillna(0).astype(int)


def funnel_by_source(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    rows = []
    for source, g in df.groupby("source"):
        applied = len(g)
        interviews = int(g["stage"].isin(_INTERVIEW_STAGES).sum())
        rows.append(
            {
                "source": source,
                "applications": applied,
                "reached_interview": interviews,
                "1st_round": int(_reached(g, "phone_1").sum()),
                "2nd_round": int(_reached(g, "interview_2").sum()),
                "3rd_round": int(_reached(g, "interview_3").sum()),
                "final_round": int(_reached(g, "onsite_final").sum()),
                "offers": int(g["offer"].sum()),
                "interview_rate": round(interviews / applied, 3) if applied else 0,
                "offer_rate": round(int(g["offer"].sum()) / applied, 3) if applied else 0,
                "interviews_per_app": round(interviews / applied, 2) if applied else 0,
            }
        )
    out = pd.DataFrame(rows).sort_values("applications", ascending=False)
    total = {
        "source": "TOTAL",
        "applications": out["applications"].sum(),
        "reached_interview": out["reached_interview"].sum(),
        "1st_round": out["1st_round"].sum(),
        "2nd_round": out["2nd_round"].sum(),
        "3rd_round": out["3rd_round"].sum(),
        "final_round": out["final_round"].sum(),
        "offers": out["offers"].sum(),
    }
    total["interview_rate"] = (
        round(total["reached_interview"] / total["applications"], 3) if total["applications"] else 0
    )
    total["offer_rate"] = (
        round(total["offers"] / total["applications"], 3) if total["applications"] else 0
    )
    total["interviews_per_app"] = total["interview_rate"]
    return pd.concat([out, pd.DataFrame([total])], ignore_index=True)


def all_metrics(df: pd.DataFrame) -> dict:
    return {
        "weekly_applications": weekly_applications(df),
        "weekly_interviews_by_level": weekly_interviews_by_level(df),
        "weekly_interviews_by_source": weekly_interviews_by_source(df),
        "weekly_offers": weekly_offers(df),
        "funnel_by_source": funnel_by_source(df),
    }
