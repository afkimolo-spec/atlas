FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src \
    ATLAS_ROOT=/app \
    ATLAS_CONFIG_DIR=/app/configs

WORKDIR /app

RUN useradd \
        --create-home \
        --uid 10001 \
        atlas

COPY pyproject.toml README.md /app/
COPY src /app/src
COPY configs /app/configs
COPY tools /app/tools

RUN pip install \
        --no-cache-dir \
        --disable-pip-version-check \
        .

RUN mkdir -p \
        /app/.ai/memory/db \
        /app/logs \
        /app/run \
        /app/runtime && \
    chown -R atlas:atlas /app

USER atlas

EXPOSE 8080

HEALTHCHECK \
    --interval=15s \
    --timeout=5s \
    --start-period=30s \
    --retries=5 \
    CMD python -c "\
import urllib.request; \
urllib.request.urlopen('http://127.0.0.1:8080/ready', timeout=3).read()\
"

STOPSIGNAL SIGTERM

CMD ["python", "-m", "atlas.api.server"]
