FROM python:3.11-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y gcc && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==1.7.1

# Копируем зависимости только этого сервиса
COPY services/api-gateway/pyproject.toml services/api-gateway/poetry.lock* ./

RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-root --no-interaction --no-ansi

RUN pip install grpcio-tools prometheus-fastapi-instrumentator orjson


# === Production stage ===
FROM base AS production

WORKDIR /app

# Копируем proto и исходники
COPY proto proto
COPY services/api-gateway/app app

# Создаём директорию под сгенерированные файлы
RUN mkdir -p app/proto

# Генерируем gRPC файлы
RUN python -m grpc_tools.protoc \
    -Iproto \
    --python_out=app/proto \
    --grpc_python_out=app/proto \
    --pyi_out=app/proto \
    proto/*.proto

# Фиксим импорты
RUN find app/proto -name "*_pb2_grpc.py" -exec sed -i 's/^import \([a-z_]*\)_pb2/from . import \1_pb2/' {} \;

# Добавляем __init__.py
RUN touch app/proto/__init__.py

# Проверка
RUN echo "=== Generated proto files ===" && ls -la app/proto/

EXPOSE 8000 9090
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
