FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN pip install poetry && poetry install --only main --no-root
COPY app/ ./app/
CMD ["python", "-m", "app.server"]