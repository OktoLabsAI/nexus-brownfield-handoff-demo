# One-click Railway image: Okto Nexus behind a Caddy proxy. See deploy/nexus/README.md.
# Build context = repo root. On Railway set RAILWAY_DOCKERFILE_PATH=deploy/nexus/Dockerfile.
# serve-lite skips the PyTorch/embedding stack (about 6 GB); semantic memory is not enabled here.
FROM caddy:2 AS caddy
FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DEFAULT_TIMEOUT=120 PIP_RETRIES=10 NEXUS_HOME=/data
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY --from=caddy /usr/bin/caddy /usr/local/bin/caddy
RUN pip install "okto-nexus[serve-lite]"
WORKDIR /app
COPY deploy/nexus/Caddyfile deploy/nexus/entrypoint.sh /app/
RUN chmod +x /app/entrypoint.sh && mkdir -p /workspace
EXPOSE 8080
CMD ["/app/entrypoint.sh"]
