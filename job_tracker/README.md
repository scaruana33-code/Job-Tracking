# 📈 Job-Search Analytics Pipeline

A Python system that pulls your job-application activity from your **Excel
tracker**, **relational databases**, **Gmail**, and your **LinkedIn data
export**, unifies it into one clean fact table, and serves an auto-refreshing
**dashboard**, a weekly **email digest**, and a **live-updated Excel tracker**.

It answers, **per week and broken out by application source** (cold-applied via
ATS · LinkedIn · networking/referral · recruiter-initiated):

- How many jobs you applied to
- How many reached an interview, and **at which round** (1st phone, 2nd, 3rd,
  onsite/final)
- How many offers you received
- Conversion rates: interview-per-application and offer-per-application

## How to refresh — the part you asked about

```bash
# 1. Manual one-time refresh (most common)
python -m job_tracker.cli refresh          # pull → normalize → warehouse → Excel → email
python -m job_tracker.cli refresh --no-email

# 2. Automatic, on a cadence (default: Mondays 07:00 America/New_York)
python -m job_tracker.cli schedule         # runs once now, then repeats forever

# 3. From the dashboard — click "🔄 Refresh data now"
streamlit run job_tracker/dashboard.py
```

Every refresh reads your tracker's manual rows, merges them with the other
feeds, **writes the unified result back into the Applications sheet, and
recomputes the Dashboard and Source Analysis tabs.**

## Quick start (60 seconds, no credentials)

```bash
pip install -r requirements.txt
mkdir -p data && cp /path/to/Executive_Job_Search_Tracker.xlsx data/

python -m job_tracker.cli demo             # load synthetic data + fill the tracker
python -m job_tracker.cli report           # print the funnel
streamlit run job_tracker/dashboard.py     # interactive dashboard
```

## Architecture

```
 ┌────────┐ ┌────────────┐ ┌────────┐ ┌─────────────────┐
 │ Excel  │ │ Relational │ │ Gmail  │ │ LinkedIn export │  (sources)
 │tracker │ │  DBs (n)   │ │  API   │ │      CSV        │
 └───┬────┘ └─────┬──────┘ └───┬────┘ └────────┬────────┘
     │ sources_excel  sources_db  sources_gmail sources_linkedin
     └─────────────┴──────────┴──────────┴────────┘
                       │  raw events
                 ┌─────▼─────┐
                 │ normalize │  role-aware collapse → 1 row per application
                 └─────┬─────┘
                       │  applications_fact (SQLite/Postgres warehouse)
        ┌──────────────┼──────────────┬───────────────┐
   ┌────▼────┐    ┌────▼─────┐   ┌────▼─────┐    ┌─────▼──────┐
   │ metrics │    │ report → │   │ Excel    │    │ dashboard  │
   │ weekly  │    │  Gmail   │   │ write-   │    │ Streamlit  │
   │ rollups │    │  digest  │   │ back     │    │ + Plotly   │
   └─────────┘    └──────────┘   └──────────┘    └────────────┘
        ▲
   ┌────┴─────┐
   │scheduler │  APScheduler cron → runs the whole pipeline on cadence
   └──────────┘
```

## Wire up your real data

Copy `cp .env.example .env` and fill in values.

- **Excel** — `TRACKER_XLSX` points at your tracker (default `data/…xlsx`).
  Set `TRACKER_WRITE_BACK=0` if you only want to read, not write.
- **Databases** — set `ATS_DB_URL` / `MANUAL_DB_URL` to SQLAlchemy URLs and edit
  the SELECTs in `config.py::_db_sources()`.
- **Gmail** — set `GMAIL_ENABLED=1`, drop `credentials.json` (OAuth Desktop
  client) in the folder; first run authorises read+send, caches `token.json`.
- **LinkedIn** ⚠️ — no public API for your own history and scraping breaks ToS.
  Use the official export (*Settings & Privacy ▸ Data Privacy ▸ Get a copy of
  your data ▸ "Job Applications"*) and point `LINKEDIN_EXPORT` at the CSV.

## Same company, multiple roles — how de-dupe works

`normalize.py` uses **two-pass, role-aware matching**:

1. **Anchors** — events with a real job title (Excel / DB / LinkedIn rows) get a
   bucket keyed by *normalised company + normalised role*. Seniority noise is
   stripped, so `Sr. Program Manager II` == `Program Manager`, but `Program
   Manager` ≠ `Data Analyst`.
2. **Loose events** — Gmail notifications (whose "role" is a subject line) attach
   to the **nearest anchor at the same company by time proximity**.

Verified by test: applying to Stripe for *Program Manager* (July) **and** *Data
Analyst* (August) yields two applications; a mid-July "2nd round" email attaches
to the PM and an August "offer" attaches to the Data Analyst.

## Deploying it (runs on cadence, unattended)

**Docker (recommended)**
```bash
cp .env.example .env
docker compose up -d --build     # scheduler + dashboard; UI on :8501
docker compose logs -f scheduler
```

**Bare metal (systemd)**
```bash
sudo bash deploy/install_baremetal.sh
sudo systemctl status job-tracker-scheduler
```

## File map

| File | Purpose |
|------|---------|
| `config.py` | Settings & source definitions (env-driven) |
| `schema.py` | Canonical columns + source/stage vocabularies |
| `classify.py` | Regex classifiers for source & interview stage |
| `sources_excel.py` | **Read + write-back** your tracker |
| `sources_db.py` | Pull from relational DBs (SQLAlchemy) |
| `sources_gmail.py` | Gmail read (events) + send (digest) |
| `sources_linkedin.py` | Ingest LinkedIn official export CSV |
| `normalize.py` | Role-aware collapse → 1 row per application |
| `metrics.py` | Weekly rollups + funnel-by-source |
| `report.py` | HTML weekly digest |
| `dashboard.py` | Streamlit + Plotly UI, manual + auto refresh |
| `scheduler.py` | APScheduler cadence runner |
| `pipeline.py` | Orchestrator (pull→normalize→persist→Excel→email) |
| `cli.py` | `refresh` / `demo` / `schedule` / `report` |
| `demo_data.py` | Synthetic data generator |

## Notes & limitations

- `source` and interview `stage` are inferred from text; tune the patterns in
  `classify.py` and `_norm_role` in `normalize.py` for your own wording.
- Round-date columns in the tracker are written as `X` markers (reached-flags);
  swap for real dates in `sources_excel._write_applications` if you prefer.
- Only lawful, ToS-compliant data access is used. No scraping.
