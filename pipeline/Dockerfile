# Standalone image for the Online Retail II batch pipeline.
#
# Installs only the runtime dependencies used by pipeline/scripts. The FastAPI
# application, AI SDKs, and Airflow are intentionally excluded.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp \
    PYTHONPATH=/app

WORKDIR /app

COPY requirements.txt /tmp/pipeline-requirements.txt
RUN python -m pip install --no-cache-dir -r /tmp/pipeline-requirements.txt \
    && python -m pip check \
    && rm -f /tmp/pipeline-requirements.txt

# Non-root runtime user. Compose can override UID/GID to match host data
# ownership via PIPELINE_UID and PIPELINE_GID.
RUN groupadd --gid 50000 pipeline \
    && useradd --uid 50000 --gid 50000 --no-create-home --shell /usr/sbin/nologin pipeline \
    && mkdir -p /app/pipeline \
    && chown 50000:50000 /app/pipeline

COPY --chown=50000:50000 scripts /app/pipeline/scripts
COPY --chown=50000:50000 run_pipeline.py /app/pipeline/run_pipeline.py

USER 50000:50000
WORKDIR /app

ENTRYPOINT ["python", "-m", "pipeline.run_pipeline"]
