FROM python:3.11-slim as base

WORKDIR /app

RUN pip install --no-cache-dir poetry==1.7.1

COPY pyproject.toml ./
RUN poetry config virtualenvs.create false && \
    poetry install --only main --no-root --no-interaction --no-ansi

FROM base as production

COPY ./app ./app

EXPOSE 50054 9090

CMD ["python", "-m", "app.main"]
