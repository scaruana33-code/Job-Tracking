"""
Interactive dashboard (Streamlit + Plotly).

Run:  streamlit run job_tracker/dashboard.py
"""
from __future__ import annotations

import datetime as dt

import plotly.express as px
import streamlit as st

from . import metrics as M
from .config import CONFIG
from .pipeline import load_fact, run_pipeline

st.set_page_config(page_title="Job Search Analytics", page_icon="📈", layout="wide")

REFRESH_MINUTES = 30
try:
    from streamlit_autorefresh import st_autorefresh

    st_autorefresh(interval=REFRESH_MINUTES * 60 * 1000, key="auto")
except Exception:
    pass

st.title("📈 Job Search Analytics Dashboard")

with st.sidebar:
    st.header("Controls")
    if st.button("🔄 Refresh data now", use_container_width=True):
        with st.spinner("Pulling from Excel, DBs, Gmail & LinkedIn..."):
            run_pipeline(send_email=False)
        st.success("Refreshed!")
    st.caption(
        f"Scheduled auto-pull: {CONFIG.refresh_cron['day_of_week']} "
        f"{CONFIG.refresh_cron['hour']}:{CONFIG.refresh_cron['minute'].zfill(2)} "
        f"({CONFIG.timezone})"
    )

fact = load_fact(CONFIG.warehouse_url)
if fact.empty:
    st.warning("No data yet. Click **Refresh data now**, or run `python -m job_tracker.cli demo`.")
    st.stop()

min_d = fact["applied_at"].min().date()
max_d = fact["applied_at"].max().date()
with st.sidebar:
    dr = st.date_input("Date range", (min_d, max_d), min_value=min_d, max_value=max_d)
    src_filter = st.multiselect(
        "Sources", sorted(fact["source"].unique()), default=sorted(fact["source"].unique())
    )

mask = fact["source"].isin(src_filter)
if isinstance(dr, tuple) and len(dr) == 2:
    mask &= fact["applied_at"].dt.date.between(dr[0], dr[1])
view = fact[mask].copy()
m = M.all_metrics(view)

_IV = ["phone_1", "interview_2", "interview_3", "onsite_final", "offer"]
last_week = view["week"].max()
tw = view[view["week"] == last_week]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Applications (all-time)", len(view))
c2.metric("Interviews reached", int(view["stage"].isin(_IV).sum()))
c3.metric("Offers", int(view["offer"].sum()))
c4.metric("Apps this week", len(tw))

st.subheader("Applications per week — by source")
wa = m["weekly_applications"]
if not wa.empty:
    long = wa.reset_index().melt("week", var_name="source", value_name="applications")
    fig = px.bar(long, x="week", y="applications", color="source", barmode="stack")
    fig.update_layout(height=380, legend_title="Source")
    st.plotly_chart(fig, use_container_width=True)

st.subheader("Interviews per week — by round / level")
wl = m["weekly_interviews_by_level"]
if not wl.empty:
    long = wl.reset_index().melt("week", var_name="round", value_name="count")
    fig = px.bar(long, x="week", y="count", color="round", barmode="group")
    fig.update_layout(height=380, legend_title="Round")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No interview-stage events detected yet.")

st.subheader("Offers per week — by source")
wo = m["weekly_offers"]
if wo is not None and not wo.empty and wo.values.sum() > 0:
    long = wo.reset_index().melt("week", var_name="source", value_name="offers")
    fig = px.bar(long, x="week", y="offers", color="source", barmode="stack")
    fig.update_layout(height=320, legend_title="Source")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("No offers recorded yet — keep going! 💪")

st.subheader("Conversion funnel — by application source")
st.dataframe(
    m["funnel_by_source"].style.format(
        {"interview_rate": "{:.0%}", "offer_rate": "{:.0%}", "interviews_per_app": "{:.2f}"}
    ),
    use_container_width=True,
)

st.caption(f"Last rendered {dt.datetime.now():%Y-%m-%d %H:%M}. Warehouse: {CONFIG.warehouse_url}")
