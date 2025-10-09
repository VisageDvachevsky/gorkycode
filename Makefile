DOCKER_COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

.PHONY: help up down build rebuild logs clean install test lint format check shell-backend shell-frontend shell-db restart-backend restart-frontend load-data

help:
	@echo "AI-Tourist Development Commands:"
	@echo ""
	@echo "  make up              - Start all services"
	@echo "  make down            - Stop all services"
	@echo "  make build           - Build all containers"
	@echo "  make rebuild         - Rebuild and restart"
	@echo "  make logs            - Show logs (all services)"
	@echo "  make logs-api        - Show backend logs"
	@echo "  make logs-frontend   - Show frontend logs"
	@echo "  make clean           - Remove volumes and containers"
	@echo "  make install         - Install all dependencies"
	@echo "  make test            - Run tests"
	@echo "  make lint            - Run linters"
	@echo "  make format          - Format code"
	@echo "  make check           - Run system check"
	@echo "  make load-data       - Load POI data into database"

up:
	$(DOCKER_COMPOSE) up -d

down:
	$(DOCKER_COMPOSE) down

build:
	$(DOCKER_COMPOSE) build --progress=plain

rebuild: down
	$(DOCKER_COMPOSE) build
	$(DOCKER_COMPOSE) up -d
	@echo ""
	@echo "✅ Services rebuilt and started"
	@echo "Backend API: http://localhost:8000"
	@echo "Frontend: http://localhost:5173"
	@echo "Docs: http://localhost:8000/docs"

logs:
	$(DOCKER_COMPOSE) logs -f

logs-api:
	$(DOCKER_COMPOSE) logs -f backend

logs-frontend:
	$(DOCKER_COMPOSE) logs -f frontend

logs-db:
	$(DOCKER_COMPOSE) logs -f db

clean:
	$(DOCKER_COMPOSE) down -v --remove-orphans
	docker system prune -f
	@echo "✅ Cleaned up containers, volumes, and orphaned resources"

install:
	@echo "Installing backend dependencies..."
	$(DOCKER_COMPOSE) run --rm backend poetry install
	@echo "Installing frontend dependencies..."
	$(DOCKER_COMPOSE) run --rm frontend npm install
	@echo "✅ All dependencies installed"

test:
	$(DOCKER_COMPOSE) exec backend poetry run pytest -v

lint:
	@echo "Running backend linters..."
	$(DOCKER_COMPOSE) exec backend poetry run ruff check app/
	$(DOCKER_COMPOSE) exec backend poetry run mypy app/

format:
	@echo "Formatting backend code..."
	$(DOCKER_COMPOSE) exec backend poetry run black app/
	$(DOCKER_COMPOSE) exec backend poetry run isort app/
	@echo "✅ Code formatted"

check:
	$(DOCKER_COMPOSE) exec backend poetry run python scripts/check_system.py

load-data:
	$(DOCKER_COMPOSE) exec backend poetry run python scripts/load_pois.py

shell-backend:
	$(DOCKER_COMPOSE) exec backend /bin/bash

shell-frontend:
	$(DOCKER_COMPOSE) exec frontend /bin/sh

shell-db:
	$(DOCKER_COMPOSE) exec db psql -U aitourist -d aitourist_db

restart-backend:
	$(DOCKER_COMPOSE) restart backend

restart-frontend:
	$(DOCKER_COMPOSE) restart frontend