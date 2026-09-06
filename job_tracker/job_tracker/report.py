"""Build the weekly HTML digest emailed to your Gmail inbox."""
from __future__ import annotations

import datetime as dt

import pandas as pd

from . import metrics as M

_INTERVIEW_STAGES = ["phone_1", "interview_2", "interview_3", "onsite_final", "offer"]


def _table(df: pd.DataFrame, title: str) -> str:
    if df is None or df.empty:
        return f"<h3>{title}</h3><p><i>No data yet.</i></p>"
    return f"<h3>{title}</h3>" + df.to_html(border=0, classes="tbl")


def build_digest_html(fact: pd.DataFrame) -> tuple[str, str]:
    m = M.all_metrics(fact)
    today = dt.date.today().isoformat()

    last_week = fact["week"].max() if not fact.empty else None
    this_week = fact[fact["week"] == last_week] if last_week is not None else fact
    apps = len(this_week)
    ivs = int(this_week["stage"].isin(_INTERVIEW_STAGES).sum())
    offers = int(this_week["offer"].sum())

    style = """
    <style>
      body{font-family:Segoe UI,Arial,sans-serif;color:#222}
      .tbl{border-collapse:collapse;margin:8px 0 20px}
      .tbl td,.tbl th{border:1px solid #ddd;padding:6px 10px;font-size:13px}
      .tbl th{background:#0a66c2;color:#fff}
      .kpi{display:inline-block;margin:6px 18px 6px 0;font-size:15px}
      .kpi b{font-size:22px;color:#0a66c2}
    </style>
    """
    kpis = f"""
    <div>
      <span class="kpi"><b>{apps}</b><br>Applications this week</span>
      <span class="kpi"><b>{ivs}</b><br>Interviews reached</span>
      <span class="kpi"><b>{offers}</b><br>Offers this week</span>
    </div>
    """
    html = f"""
    <html><head>{style}</head><body>
    <h2>📈 Job Search Weekly Digest — {today}</h2>
    {kpis}
    {_table(m['funnel_by_source'], "Funnel by application source (all-time)")}
    {_table(m['weekly_applications'].tail(8), "Applications per week (by source)")}
    {_table(m['weekly_interviews_by_level'].tail(8), "Interviews per week (by round)")}
    {_table(m['weekly_offers'].tail(8), "Offers per week (by source)")}
    <p style="color:#888;font-size:12px">Generated automatically by your Job-Tracker pipeline.</p>
    </body></html>
    """
    subject = f"Job Search Digest {today}: {apps} apps, {ivs} interviews, {offers} offers"
    return html, subject
