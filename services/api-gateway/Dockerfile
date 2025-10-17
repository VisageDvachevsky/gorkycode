FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==1.7.1

COPY services/api-gateway/pyproject.toml services/api-gateway/poetry.lock* ./

RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-root --no-interaction --no-ansi

RUN pip install grpcio-tools

FROM base AS production

WORKDIR /app

# Копируем proto из корня проекта
COPY proto/ ./proto/

# Создаем директорию для proto ПЕРЕД копированием app
RUN mkdir -p ./app/grpc/proto

# Generate proto files ПЕРЕД копированием app
RUN python -m grpc_tools.protoc \
    -I./proto \
    --python_out=./app/grpc/proto \
    --grpc_python_out=./app/grpc/proto \
    --pyi_out=./app/grpc/proto \
    ./proto/*.proto

# Фиксим импорты
RUN find ./app/grpc/proto -name "*_pb2_grpc.py" -exec sed -i 's/^import \([a-z_]*\)_pb2/from . import \1_pb2/' {} \;

# Создаем __init__.py
RUN touch ./app/grpc/proto/__init__.py

# ТЕПЕРЬ копируем app (без перезаписи proto)
COPY services/api-gateway/app ./app

# Проверяем что proto на месте
RUN echo "Generated proto files:" && ls -la ./app/grpc/proto/ && \
    echo "Testing import..." && python -c "from app.grpc.proto import poi_pb2; print('✓ Import successful')"

EXPOSE 8000 9090

ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]