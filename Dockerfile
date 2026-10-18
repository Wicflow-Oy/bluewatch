# BlueWatch: one container serving the API and the built front end.
# Build: docker build -t jx-bluewatch:latest .

FROM node:24-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim AS app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    BLUEWATCH_PUBLIC=1 \
    BLUEWATCH_OFFLINE=1 \
    OUTREACH_MODE=demo \
    BLUEWATCH_SKIP_ENV_LOCAL=1 \
    BLUEWATCH_CACHE_DIR=/tmp/bluewatch-cache \
    FORWARDED_ALLOW_IPS=*
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt && useradd --system --uid 10001 --no-create-home bluewatch \
    && mkdir /state && chown bluewatch /state
COPY bluewatch ./bluewatch
# All runtime data: seeds, presets, recorded fixtures, eval sets and recorded reads (.dockerignore drops caches).
COPY data ./data
COPY --from=web /web/dist ./frontend/dist
USER bluewatch
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8787/api/health', timeout=4).status == 200 else 1)"
# /state: the spend ledger's directory; compose mounts a small volume there (see deploy/compose.yml).
# --proxy-headers: Traefik sets X-Forwarded-For, which the per-IP limit reads. There are no host ports, but
#   other containers on Traefik's network can reach this one too: set FORWARDED_ALLOW_IPS in .env to
#   Traefik's address or subnet so only Traefik's header is trusted (the compose files pass it through;
#   left empty it stays *). BLUEWATCH_BUILD (the deployed commit, see DEPLOY.md) is passed the same way.
# --no-access-log: no request lines in the logs (visitor input is never logged).
CMD ["uvicorn", "bluewatch.api.app:app", "--host", "0.0.0.0", "--port", "8787", "--proxy-headers", "--no-access-log", "--no-server-header"]
