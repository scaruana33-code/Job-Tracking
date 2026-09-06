"""
Central configuration. Secrets come from environment variables (see .env.example)
so nothing sensitive is hard-coded.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Dict, List


# --------------------------------------------------------------------------- #
#  Relational database sources
# --------------------------------------------------------------------------- #
@dataclass
class DBSource:
    name: str                     # friendly label, e.g. "company_ats"
    url: str                      # SQLAlchemy URL (postgres/mysql/mssql/sqlite)
    query: str                    # SELECT returning canonical-ish columns
    default_source: str = "ats"   # tag rows when the query has no `source` column


def _db_sources() -> List[DBSource]:
    sources: List[DBSource] = []

    if os.getenv("ATS_DB_URL"):
        sources.append(
            DBSource(
                name="company_ats",
                url=os.environ["ATS_DB_URL"],
                default_source="ats",
                query="""
                    SELECT  a.id            AS application_id,
                            c.name          AS company,
                            j.title         AS role,
                            a.submitted_at  AS applied_at,
                            'ats'           AS source,
                            a.current_stage AS stage,
                            a.stage_level   AS stage_level,
                            a.offer_flag    AS offer,
                            a.notes         AS notes
                    FROM    applications a
                    JOIN    jobs j      ON j.id = a.job_id
                    JOIN    companies c ON c.id = j.company_id
                """,
            )
        )

    if os.getenv("MANUAL_DB_URL"):
        sources.append(
            DBSource(
                name="manual_log",
                url=os.environ["MANUAL_DB_URL"],
                default_source="networking",
                query="SELECT * FROM applications",
            )
        )

    return sources


# --------------------------------------------------------------------------- #
#  Excel tracker source (your Executive_Job_Search_Tracker.xlsx)
# --------------------------------------------------------------------------- #
@dataclass
class ExcelConfig:
    # Read rows FROM this tracker and write the refreshed result back TO it.
    path: str = os.getenv("TRACKER_XLSX", "data/Executive_Job_Search_Tracker.xlsx")
    write_back: bool = os.getenv("TRACKER_WRITE_BACK", "1") not in ("0", "false", "False")


# --------------------------------------------------------------------------- #
#  Gmail source
# --------------------------------------------------------------------------- #
@dataclass
class GmailConfig:
    enabled: bool = os.getenv("GMAIL_ENABLED", "0") not in ("0", "false", "False")
    credentials_file: str = os.getenv("GMAIL_CREDENTIALS", "credentials.json")
    token_file: str = os.getenv("GMAIL_TOKEN", "token.json")
    query: str = os.getenv(
        "GMAIL_QUERY",
        'newer_than:120d (application OR interview OR "thank you for applying" '
        'OR offer OR recruiter OR "next steps" OR "schedule a call")',
    )
    notify_to: str = os.getenv("NOTIFY_EMAIL", "you@gmail.com")


# --------------------------------------------------------------------------- #
#  LinkedIn source (official export CSV; NO scraping)
# --------------------------------------------------------------------------- #
@dataclass
class LinkedInConfig:
    export_csv: str = os.getenv("LINKEDIN_EXPORT", "data/linkedin_job_applications.csv")


# --------------------------------------------------------------------------- #
#  Top-level config
# --------------------------------------------------------------------------- #
@dataclass
class AppConfig:
    db_sources: List[DBSource] = field(default_factory=_db_sources)
    excel: ExcelConfig = field(default_factory=ExcelConfig)
    gmail: GmailConfig = field(default_factory=GmailConfig)
    linkedin: LinkedInConfig = field(default_factory=LinkedInConfig)

    warehouse_url: str = os.getenv("WAREHOUSE_URL", "sqlite:///data/job_tracker.db")

    refresh_cron: Dict[str, str] = field(
        default_factory=lambda: {
            "day_of_week": os.getenv("REFRESH_DOW", "mon"),
            "hour": os.getenv("REFRESH_HOUR", "7"),
            "minute": os.getenv("REFRESH_MIN", "0"),
        }
    )
    timezone: str = os.getenv("TZ", "America/New_York")


CONFIG = AppConfig()
