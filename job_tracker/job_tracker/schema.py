"""Canonical schema + controlled vocabularies (shared by every connector)."""
from __future__ import annotations

# Canonical columns of the unified "applications" fact table
CANONICAL_COLUMNS = [
    "application_id",   # stable unique id (str)
    "company",          # employer name
    "role",             # job title
    "applied_at",       # datetime the application was submitted
    "source",           # one of SOURCES below
    "stage",            # furthest stage reached (see STAGE_ORDER)
    "stage_level",      # integer ordering of the stage
    "offer",            # bool – did this app result in an offer
    "origin",           # which connector produced the row (db/gmail/linkedin/excel)
    "notes",            # free text
]

# ---- How the application originated ------------------------------------- #
SOURCES = [
    "ats",         # cold-applied through a company ATS / careers site
    "linkedin",    # applied via LinkedIn (Easy Apply or LinkedIn job)
    "networking",  # a referral / warm intro / networking contact
    "recruiter",   # a recruiter saw your profile and initiated the process
    "unknown",
]

# ---- Interview funnel stages -------------------------------------------- #
STAGE_ORDER = {
    "applied": 0,
    "screen": 1,          # recruiter / HR screen
    "phone_1": 2,         # 1st round phone / technical screen
    "interview_2": 3,     # 2nd round
    "interview_3": 4,     # 3rd round
    "onsite_final": 5,    # onsite / final loop
    "offer": 6,
    "rejected": -1,       # terminal, does not advance the funnel
}
STAGES = list(STAGE_ORDER.keys())

STAGE_LABELS = {
    "applied": "Applied",
    "screen": "Recruiter Screen",
    "phone_1": "1st Round (Phone)",
    "interview_2": "2nd Round",
    "interview_3": "3rd Round",
    "onsite_final": "Onsite / Final",
    "offer": "Offer",
    "rejected": "Rejected",
}
