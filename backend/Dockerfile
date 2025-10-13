# syntax=docker/dockerfile:1

# ==================== Base Configuration ====================
FROM python:3.11-slim as python-base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

ENV POETRY_VERSION=1.8.4 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    POETRY_VIRTUALENVS_CREATE=true \
    POETRY_NO_INTERACTION=1 \
    POETRY_REQUESTS_TIMEOUT=300 \
    POETRY_INSTALLER_MAX_WORKERS=4

ENV PYSETUP_PATH="/opt/pysetup" \
    VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$POETRY_HOME/bin:$VENV_PATH/bin:$PATH"

# ==================== Builder Stage ====================
FROM python-base as builder

RUN apt-get update && apt-get install --no-install-recommends -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install "poetry==$POETRY_VERSION"

WORKDIR $PYSETUP_PATH

COPY poetry.lock pyproject.toml ./

# Создаем virtualenv вручную
RUN python -m venv $VENV_PATH

# КРИТИЧНО: устанавливаем numpy 1.x ПЕРВЫМ делом
RUN --mount=type=cache,target=/root/.cache/pip \
    $VENV_PATH/bin/pip install "numpy>=1.26.0,<2.0"

# Теперь устанавливаем остальные зависимости через Poetry
RUN --mount=type=cache,target=/root/.cache/pypoetry \
    poetry install --only main --no-root --no-directory

# Установка PyTorch CPU-only
RUN --mount=type=cache,target=/root/.cache/pip \
    $VENV_PATH/bin/pip install \
    torch==2.1.2 \
    torchvision==0.16.2 \
    --index-url https://download.pytorch.org/whl/cpu

# Установка ML библиотек
RUN --mount=type=cache,target=/root/.cache/pip \
    $VENV_PATH/bin/pip install \
    transformers==4.36.2 \
    sentence-transformers==2.3.1 \
    scikit-learn==1.4.0

COPY . .

# Установка самого проекта
RUN poetry install --only main

# ==================== Production Runtime ====================
FROM python:3.11-slim as production

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    VENV_PATH="/opt/pysetup/.venv"

ENV PATH="$VENV_PATH/bin:$PATH"

RUN groupadd -g 1000 appuser && \
    useradd -u 1000 -g appuser -m -d /home/appuser appuser

WORKDIR /app

COPY --from=builder --chown=appuser:appuser $VENV_PATH $VENV_PATH
COPY --from=builder --chown=appuser:appuser /opt/pysetup/app ./app
COPY --from=builder --chown=appuser:appuser /opt/pysetup/scripts ./scripts

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]