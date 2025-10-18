FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==1.7.1

# КРИТИЧНО: Копируем из services/embedding-service/
COPY services/embedding-service/pyproject.toml services/embedding-service/poetry.lock* ./

RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-root --no-interaction --no-ansi

# Pre-download embedding model
RUN pip install sentence-transformers && \
    python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

FROM base AS production

WORKDIR /app

# Copy proto files from project root
COPY proto/ ./proto/

# Copy service code
COPY services/embedding-service/app ./app

# Create proto directory
RUN mkdir -p ./app/proto

# Generate proto files
RUN pip install grpcio-tools && \
    python -m grpc_tools.protoc \
        -I./proto \
        --python_out=./app/proto \
        --grpc_python_out=./app/proto \
        --pyi_out=./app/proto \
        ./proto/*.proto

# Fix imports
RUN find ./app/proto -name "*_pb2_grpc.py" -exec sed -i 's/^import \([a-z_]*\)_pb2/from . import \1_pb2/' {} \;

# Create __init__.py
RUN touch ./app/proto/__init__.py

EXPOSE 50051 9091

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "app.main"]
