FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TERRARIUM_DATA_DIR=/data

WORKDIR /app

RUN addgroup --system terrarium \
    && adduser --system --ingroup terrarium terrarium

COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY examples ./examples

RUN python -m pip install --no-cache-dir . \
    && mkdir -p /data \
    && chown terrarium:terrarium /data

USER terrarium
EXPOSE 8700

HEALTHCHECK --interval=15s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8700/readyz', timeout=2).read()"]

CMD ["terrarium", "service", "--task", "examples/tasks/inbox-triage.yaml", \
     "--data-dir", "/data", "--host", "0.0.0.0", "--port", "8700", \
     "--allow-remote"]
