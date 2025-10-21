FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==1.7.1

COPY services/poi-service/pyproject.toml services/poi-service/poetry.lock* ./
COPY services/python-common /python-common

RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-root --no-interaction --no-ansi

FROM base AS production

WORKDIR /app

COPY proto/ ./proto/
COPY services/poi-service/app ./app
COPY services/poi-service/scripts/ ./scripts/
COPY scripts/poi_loader_utils.py ./scripts/

RUN mkdir -p ./app/proto

RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./app/proto \
    --grpc_python_out=./app/proto \
    --pyi_out=./app/proto \
    ./proto/*.proto

RUN find ./app/proto -name "*_pb2_grpc.py" -exec sed -i 's/^import \([a-z_]*\)_pb2/from . import \1_pb2/' {} \;

RUN touch ./app/proto/__init__.py

RUN echo "=== Generated proto files ===" && ls -la ./app/proto/

RUN echo "=== Scripts directory ===" && ls -la ./scripts/

RUN mkdir -p /app/data

EXPOSE 50056 9096

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "app.main"]
