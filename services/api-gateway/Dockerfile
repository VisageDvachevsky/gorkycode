FROM python:3.11-slim as base

WORKDIR /app

RUN pip install --no-cache-dir poetry==1.7.1

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

FROM base as production

COPY ./app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]