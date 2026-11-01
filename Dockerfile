# Three stages. `base` is the app with its runtime dependencies. `test` runs
# the pytest suite on top of it. `runtime` is what ships, and it copies a
# marker file from `test`, so the suite failing fails the whole build and
# Dokploy never deploys the image. The final image contains no test
# dependencies.
FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    libjpeg-dev \
    zlib1g-dev \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Matplotlib (ATMOS charts) renders headless and needs a writable cache dir
ENV MPLBACKEND=Agg MPLCONFIGDIR=/tmp/matplotlib

COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

COPY app/ ./app/
COPY content/ ./content/
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/


# ---------------------------------------------------------------------------
FROM base AS test

COPY requirements.txt requirements-dev.txt pytest.ini ./
COPY tests/ ./tests/
# requirements.txt carries the same pins as requirements.lock, so this only adds pytest and httpx.
RUN pip install --no-cache-dir -r requirements-dev.txt \
    && python -m pytest -q \
    && echo "tests passed $(date -u +%Y-%m-%dT%H:%M:%SZ)" > /tests-passed


# ---------------------------------------------------------------------------
FROM base AS runtime

# This COPY is the deploy gate: it makes `runtime` depend on `test`.
COPY --from=test /tests-passed /app/.tests-passed

RUN mkdir -p data/images

EXPOSE 8000

CMD ["bash", "-c", "bash scripts/init_db.sh && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
