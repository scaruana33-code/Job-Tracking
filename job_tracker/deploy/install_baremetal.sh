#!/usr/bin/env bash
# One-shot bare-metal installer (no Docker).
#   sudo bash deploy/install_baremetal.sh
set -euo pipefail

APP_DIR="${APP_DIR:-/opt/job_tracker}"
SERVICE_USER="${SERVICE_USER:-stephen}"

echo ">> Installing Job-Tracker to ${APP_DIR} (user: ${SERVICE_USER})"

mkdir -p "${APP_DIR}"
cp -r job_tracker requirements.txt .env.example "${APP_DIR}/"
[ -f .env ] && cp .env "${APP_DIR}/" || echo ">> No .env yet — copy .env.example to ${APP_DIR}/.env and fill it in."

python3 -m venv "${APP_DIR}/.venv"
"${APP_DIR}/.venv/bin/pip" install --upgrade pip
"${APP_DIR}/.venv/bin/pip" install -r "${APP_DIR}/requirements.txt"

mkdir -p "${APP_DIR}/data"
chown -R "${SERVICE_USER}:${SERVICE_USER}" "${APP_DIR}"

cp deploy/job-tracker-scheduler.service /etc/systemd/system/
cp deploy/job-tracker-dashboard.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now job-tracker-scheduler
systemctl enable --now job-tracker-dashboard

echo ">> Done. Dashboard on http://localhost:8501"
echo ">> Logs: journalctl -u job-tracker-scheduler -f"
