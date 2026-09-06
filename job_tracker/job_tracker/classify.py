"""
Transparent regex/keyword classifiers that turn noisy text (email subjects,
LinkedIn rows, ATS status strings) into canonical `source` and `stage` values.
"""
from __future__ import annotations

import re
from typing import Optional

from .schema import STAGE_ORDER


# ---- Source classification --------------------------------------------- #
_RECRUITER_PAT = re.compile(
    r"\b(recruiter|sourcer|talent (acquisition|partner)|came across your profile|"
    r"reached out|found your profile|i saw your (linkedin|profile)|"
    r"opportunity that (matches|fits))\b",
    re.I,
)
_NETWORK_PAT = re.compile(
    r"\b(referral|referred (by|you)|warm intro|introduc(ed|tion)|"
    r"our mutual|connected us|hiring manager (asked|suggested))\b",
    re.I,
)
_LINKEDIN_PAT = re.compile(r"\b(linkedin|easy apply)\b", re.I)
_ATS_PAT = re.compile(
    r"\b(workday|greenhouse|lever|icims|taleo|smartrecruiters|ashby|"
    r"careers?\.|jobs?\.|applied (through|via) (our|the) (site|portal|careers))\b",
    re.I,
)


def classify_source(text: str, hint: Optional[str] = None) -> str:
    t = text or ""
    if _RECRUITER_PAT.search(t):
        return "recruiter"
    if _NETWORK_PAT.search(t):
        return "networking"
    if _LINKEDIN_PAT.search(t):
        return "linkedin"
    if _ATS_PAT.search(t):
        return "ats"
    if hint in {"ats", "linkedin", "networking", "recruiter"}:
        return hint
    return "unknown"


# ---- Stage classification ---------------------------------------------- #
_OFFER_PAT = re.compile(r"\b(offer letter|pleased to offer|extend(ing)? an offer|job offer)\b", re.I)
_REJECT_PAT = re.compile(
    r"\b(unfortunately|not (moving|move) forward|decided to (proceed|move) with other|"
    r"position has been filled|will not be progressing|regret to inform)\b",
    re.I,
)
_FINAL_PAT = re.compile(r"\b(onsite|final round|final loop|super ?day|panel interview|team interview)\b", re.I)
_ROUND3_PAT = re.compile(r"\b(third|3rd)\s+(round|interview)\b", re.I)
_ROUND2_PAT = re.compile(r"\b(second|2nd)\s+(round|interview)\b", re.I)
_PHONE1_PAT = re.compile(
    r"\b(phone screen|phone interview|first (round|interview)|1st (round|interview)|"
    r"technical screen|initial (call|interview)|schedule (a )?(call|interview))\b",
    re.I,
)
_SCREEN_PAT = re.compile(r"\b(recruiter (screen|call)|hr screen|intro call|screening call)\b", re.I)
_APPLIED_PAT = re.compile(
    r"\b(thank you for applying|application received|we received your application|"
    r"successfully applied|application submitted)\b",
    re.I,
)


def classify_stage(text: str) -> str:
    t = text or ""
    if _OFFER_PAT.search(t):
        return "offer"
    if _REJECT_PAT.search(t):
        return "rejected"
    if _FINAL_PAT.search(t):
        return "onsite_final"
    if _ROUND3_PAT.search(t):
        return "interview_3"
    if _ROUND2_PAT.search(t):
        return "interview_2"
    if _PHONE1_PAT.search(t):
        return "phone_1"
    if _SCREEN_PAT.search(t):
        return "screen"
    if _APPLIED_PAT.search(t):
        return "applied"
    return "applied"


def stage_level(stage: str) -> int:
    return STAGE_ORDER.get(stage, 0)


def furthest_stage(a: str, b: str) -> str:
    return a if STAGE_ORDER.get(a, 0) >= STAGE_ORDER.get(b, 0) else b
