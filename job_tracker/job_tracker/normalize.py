"""
Collapse the raw union of all connectors into ONE clean fact table, with
role-aware de-dupe so multiple roles at one company stay distinct while noisy
Gmail events attach to the right role by time proximity.
"""
from __future__ import annotations

import re

import pandas as pd

from .classify import classify_source, classify_stage, furthest_stage, stage_level
from .schema import CANONICAL_COLUMNS

# Source attribution priority (higher wins when merging events)
_SOURCE_PRIORITY = {"recruiter": 4, "networking": 3, "linkedin": 2, "ats": 2, "unknown": 0}


def _norm_company(name) -> str:
    if not isinstance(name, str):
        return "unknown"
    n = name.lower()
    n = re.sub(r"\b(inc|llc|ltd|corp|co|gmbh|group|the)\b", "", n)
    n = re.sub(r"[^a-z0-9]", "", n)
    return n or "unknown"


# Seniority / qualifier words stripped so "Sr. Program Manager II" == "Program Manager"
_ROLE_NOISE = re.compile(
    r"\b(sr|snr|senior|jr|junior|lead|principal|staff|associate|"
    r"i{1,3}|iv|v|vi|1|2|3|contract|remote|hybrid|onsite)\b",
    re.I,
)
# Generic interview/status words that mean a Gmail "role" is really a subject line
_ROLE_STOP = re.compile(
    r"\b(interview|round|screen|offer|application|applying|next steps|"
    r"schedule|call|update|re:|fwd:|thank you|invitation)\b",
    re.I,
)


def _norm_role(role) -> str:
    if not isinstance(role, str) or not role.strip():
        return ""
    r = role.lower()
    if _ROLE_STOP.search(r):
        return ""
    r = _ROLE_NOISE.sub(" ", r)
    r = re.sub(r"[^a-z0-9]", "", r)
    return r


def normalize(raw: pd.DataFrame) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=CANONICAL_COLUMNS + ["week"])

    df = raw.copy()
    for col in CANONICAL_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df["applied_at"] = pd.to_datetime(df["applied_at"], errors="coerce", utc=True)

    # Re-derive stage/source from text where missing/unknown
    df["stage"] = df.apply(
        lambda r: r["stage"]
        if isinstance(r["stage"], str) and r["stage"]
        else classify_stage(f"{r['role']} {r['notes']}"),
        axis=1,
    )
    df["source"] = df.apply(
        lambda r: r["source"]
        if isinstance(r["source"], str) and r["source"] not in ("", "unknown", None)
        else classify_source(f"{r['role']} {r['notes']}", hint=r.get("source")),
        axis=1,
    )
    df["offer"] = df["offer"].fillna(False).astype(bool) | (df["stage"] == "offer")

    # ---- Two-pass, role-aware matching --------------------------------- #
    df["_company_key"] = df["company"].apply(_norm_company)
    df["_role_key"] = df["role"].apply(_norm_role)
    _origin = df["origin"].fillna("").astype(str)
    # Anchors carry a real role AND are not Gmail notifications
    df["_has_role"] = (df["_role_key"] != "") & (~_origin.str.startswith("gmail"))
    df.loc[_origin.str.startswith("gmail"), "_role_key"] = ""

    anchors = df[df["_has_role"]].copy()
    loose = df[~df["_has_role"]].copy()
    anchors["_key"] = anchors["_company_key"] + "|" + anchors["_role_key"]

    anchor_index: dict[str, list[tuple[str, pd.Timestamp]]] = {}
    for _, a in anchors.iterrows():
        anchor_index.setdefault(a["_company_key"], []).append((a["_key"], a["applied_at"]))

    def _assign_loose(row) -> str:
        cands = anchor_index.get(row["_company_key"])
        if not cands:
            return row["_company_key"]
        ts = row["applied_at"]
        if pd.isna(ts):
            return cands[0][0]
        return min(
            cands,
            key=lambda kt: abs((kt[1] - ts).total_seconds()) if pd.notna(kt[1]) else float("inf"),
        )[0]

    loose["_key"] = loose.apply(_assign_loose, axis=1) if not loose.empty else pd.Series(dtype=str)
    df = pd.concat([anchors, loose], ignore_index=True)

    # ---- Collapse each bucket into one application row ------------------ #
    merged = []
    for key, g in df.groupby("_key"):
        best_source = max(g["source"], key=lambda s: _SOURCE_PRIORITY.get(s, 0))
        stage = "applied"
        for s in g["stage"]:
            stage = furthest_stage(stage, s)
        has_role = g[g["_role_key"] != ""]
        display = has_role if not has_role.empty else g
        merged.append(
            {
                "application_id": display["application_id"].iloc[0],
                "company": display["company"].dropna().iloc[0]
                if display["company"].notna().any()
                else key.split("|")[0],
                "role": display["role"].dropna().iloc[0] if display["role"].notna().any() else "",
                "applied_at": g["applied_at"].min(),
                "source": best_source,
                "stage": stage,
                "stage_level": stage_level(stage),
                "offer": bool(g["offer"].any()),
                "origin": ",".join(sorted(set(g["origin"].dropna()))),
                "notes": "; ".join(sorted(set(g["notes"].dropna().astype(str))))[:500],
            }
        )

    out = pd.DataFrame(merged).dropna(subset=["applied_at"])
    out["week"] = (
        out["applied_at"].dt.tz_convert("UTC").dt.tz_localize(None)
        .dt.to_period("W-SUN").dt.start_time
    )
    return out.reset_index(drop=True)
