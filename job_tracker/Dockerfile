# ---- Job-Search Analytics Pipeline image ---------------------------------
# One image runs EITHER the scheduler OR the dashboard (see docker-compose.yml).
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=America/New_York

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY job_tracker ./job_tracker

RUN mkdir -p /app/data
VOLUME ["/app/data"]

EXPOSE 8501

CMD ["python", "-m", "job_tracker.scheduler"]
