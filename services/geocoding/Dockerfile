FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml poetry.lock* ./

RUN pip install poetry && \
    poetry config virtualenvs.in-project true && \
    poetry install --only main --no-root --no-directory

COPY . .

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

EXPOSE 50054

CMD ["python", "-m", "app.server"]
