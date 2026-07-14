# Production image for Render. Not needed for local dev — see README.md for running
# with a plain venv instead.

FROM python:3.12-slim

WORKDIR /app

# Don't write .pyc files (no benefit in a container that's rebuilt every deploy) and
# flush stdout/stderr immediately so `gunicorn --access-logfile -` output shows up in
# Render's log stream in real time instead of being buffered.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# requirements.txt copied and installed before the rest of the source so Docker's layer
# cache is reused (skip the pip install) on every rebuild that only changes app code.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# gunicorn managing uvicorn workers (rather than uvicorn directly) — restarts a worker
# that crashes instead of taking the whole process down; -w 2 is enough for a free-tier
# instance's CPU allocation.
CMD ["gunicorn", "src.api.app:app", "-k", "uvicorn.workers.UvicornWorker", "-w", "2", "--bind", "0.0.0.0:8000", "--timeout", "120"]
