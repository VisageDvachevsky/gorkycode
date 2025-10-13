FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM base as builder

COPY pyproject.toml poetry.lock* ./
RUN pip install poetry && \
    poetry config virtualenvs.in-project true && \
    poetry install --only main --no-root --no-directory

FROM base as model-downloader

ARG MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

RUN pip install torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install sentence-transformers

RUN python -c "from sentence_transformers import SentenceTransformer; \
    model = SentenceTransformer('${MODEL_NAME}'); \
    print(f'✓ Model cached with dimension {model.get_sentence_embedding_dimension()}')"

FROM base as runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    grpc-health-probe \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/.venv /app/.venv
COPY --from=model-downloader /root/.cache /root/.cache

ENV PATH="/app/.venv/bin:$PATH" \
    TRANSFORMERS_CACHE=/root/.cache \
    SENTENCE_TRANSFORMERS_HOME=/root/.cache

COPY app/ ./app/

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 50051

HEALTHCHECK --interval=10s --timeout=5s --start-period=60s --retries=3 \
    CMD grpc_health_probe -addr=:50051 || exit 1

CMD ["python", "-m", "app.server"]