FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

COPY services/api-gateway/pyproject.toml services/api-gateway/poetry.lock ./
RUN pip install poetry && \
    poetry config virtualenvs.create false && \
    poetry install --only main --no-root --no-interaction --no-ansi

RUN mkdir -p /app/app/grpc/proto && \
    touch /app/app/__init__.py && \
    touch /app/app/grpc/__init__.py

COPY proto /app/proto
COPY services/api-gateway/app /app/app

RUN python -m grpc_tools.protoc \
    --proto_path=/app/proto \
    --python_out=/app/app/grpc/proto \
    --grpc_python_out=/app/app/grpc/proto \
    --pyi_out=/app/app/grpc/proto \
    /app/proto/*.proto && \
    echo "# Proto package" > /app/app/grpc/proto/__init__.py && \
    for f in /app/app/grpc/proto/*_pb2_grpc.py; do \
        sed -i 's/^import \(.*\)_pb2 as/from . import \1_pb2 as/g' "$f"; \
    done

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]