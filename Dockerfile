# Public site only (steepseeker.com). The management/admin app is served by a
# separate process elsewhere and is excluded here (see .dockerignore).
#
# Data (data/db.db, generated static maps/thumbnails) is expected to already
# be synced into this repo checkout before `docker build` runs -- this image
# bakes in whatever is present at build time, it does not fetch or generate
# it. Rebuild + redeploy whenever the data is refreshed.
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# libexpat1: osmium's wheel links against it but doesn't bundle it.
RUN apt-get update && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Data layer: data/db.db (~165MB) and the generated static assets (~57MB) are
# synced in from elsewhere and change on a different cadence than the code
# below, so they're copied first to keep code-only rebuilds cheap.
COPY data/db.db data/db.db
COPY config/weather_calibration.json config/weather_calibration.json
COPY static/ static/

# Application code.
COPY app.py .
COPY core/ core/
COPY templates/ templates/

RUN useradd --create-home --uid 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/')" || exit 1

CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", "--error-logfile", "-", "app:app"]
