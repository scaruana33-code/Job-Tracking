"""
Connector — read job-related email from Gmail (as application events) and send
the weekly digest to your inbox.

Auth: OAuth2 desktop flow. First run opens a browser to authorise read+send;
the token caches to token.json. Scopes: gmail.readonly, gmail.send.
"""
from __future__ import annotations

import base64
import logging
import os
from email.mime.text import MIMEText
from typing import List, Optional

import pandas as pd

from .classify import classify_source, classify_stage
from .config import GmailConfig
from .schema import CANONICAL_COLUMNS

log = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
]


def _service(cfg: GmailConfig):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds: Optional[Credentials] = None
    if os.path.exists(cfg.token_file):
        creds = Credentials.from_authorized_user_file(cfg.token_file, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(cfg.credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(cfg.token_file, "w") as fh:
            fh.write(creds.to_json())
    return build("gmail", "v1", credentials=creds)


def _header(headers, name) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def _extract_body(payload) -> str:
    if payload.get("body", {}).get("data"):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8", "ignore")
    for part in payload.get("parts", []) or []:
        if part.get("mimeType") == "text/plain" and part.get("body", {}).get("data"):
            return base64.urlsafe_b64decode(part["body"]["data"]).decode("utf-8", "ignore")
        nested = _extract_body(part)
        if nested:
            return nested
    return ""


def _guess_company(sender: str, subject: str) -> str:
    m = sender
    if "<" in sender and ">" in sender:
        m = sender.split("<")[-1].strip(">")
    if "@" in m:
        domain = m.split("@")[-1].replace("mail.", "").replace("careers.", "")
        return domain.split(".")[0].title()
    return "Unknown"


def pull(cfg: GmailConfig, max_messages: int = 500) -> pd.DataFrame:
    if not cfg.enabled:
        log.info("Gmail disabled (set GMAIL_ENABLED=1 to enable).")
        return pd.DataFrame(columns=CANONICAL_COLUMNS)
    try:
        svc = _service(cfg)
    except Exception as exc:  # noqa: BLE001
        log.warning("Gmail auth/connection failed: %s", exc)
        return pd.DataFrame(columns=CANONICAL_COLUMNS)

    rows: List[dict] = []
    page_token = None
    fetched = 0
    while True:
        resp = (
            svc.users().messages()
            .list(userId="me", q=cfg.query, pageToken=page_token, maxResults=100)
            .execute()
        )
        for meta in resp.get("messages", []):
            if fetched >= max_messages:
                break
            msg = svc.users().messages().get(userId="me", id=meta["id"], format="full").execute()
            payload = msg.get("payload", {})
            headers = payload.get("headers", [])
            subject = _header(headers, "Subject")
            sender = _header(headers, "From")
            body = _extract_body(payload)
            blob = f"{subject}\n{sender}\n{body}"
            stage = classify_stage(blob)
            rows.append(
                {
                    "application_id": f"gmail:{meta['id']}",
                    "company": _guess_company(sender, subject),
                    "role": subject[:120],
                    "applied_at": pd.to_datetime(int(msg["internalDate"]), unit="ms", utc=True),
                    "source": classify_source(blob, hint=None),
                    "stage": stage,
                    "stage_level": None,
                    "offer": stage == "offer",
                    "origin": "gmail",
                    "notes": subject,
                }
            )
            fetched += 1
        page_token = resp.get("nextPageToken")
        if not page_token or fetched >= max_messages:
            break

    log.info("Gmail -> %d job-related messages", len(rows))
    df = pd.DataFrame(rows)
    return df if not df.empty else pd.DataFrame(columns=CANONICAL_COLUMNS)


def send_digest(cfg: GmailConfig, html_body: str, subject: str) -> None:
    if not cfg.enabled:
        log.info("Gmail disabled; skipping digest email.")
        return
    try:
        svc = _service(cfg)
        msg = MIMEText(html_body, "html")
        msg["to"] = cfg.notify_to
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        svc.users().messages().send(userId="me", body={"raw": raw}).execute()
        log.info("Digest emailed to %s", cfg.notify_to)
    except Exception as exc:  # noqa: BLE001
        log.warning("Failed to send digest email: %s", exc)
