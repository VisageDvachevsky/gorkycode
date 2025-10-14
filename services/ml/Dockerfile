FROM python:3.11-slim AS base

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Builder stage
FROM base AS builder

COPY pyproject.toml poetry.lock* ./

RUN pip install poetry && \
    poetry config virtualenvs.in-project true && \
    poetry install --only main --no-root --no-directory

# Model downloader stage
FROM base AS model-downloader

RUN pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install sentence-transformers

RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-mpnet-base-v2')"

# Runtime stage
FROM base AS runtime

# Install grpc-health-probe correctly
RUN GRPC_HEALTH_PROBE_VERSION=v0.4.19 && \
    curl -fsSL https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-amd64 \
    -o /usr/local/bin/grpc-health-probe && \
    chmod +x /usr/local/bin/grpc-health-probe

COPY --from=builder /app/.venv /app/.venv
COPY --from=model-downloader /root/.cache /root/.cache

COPY . .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 50051

CMD ["python", "-m", "app.main"]