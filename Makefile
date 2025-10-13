DOCKER_COMPOSE := $(shell docker compose version >/dev/null 2>&1 && echo "docker compose" || echo "docker-compose")

export DOCKER_BUILDKIT=1
export COMPOSE_DOCKER_CLI_BUILD=1

.PHONY: help up down build rebuild logs clean load-data init-db reset-db shell-backend shell-frontend shell-db restart-backend restart-frontend

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
	@echo "  make load-data       - Load POI data into database"
	@echo "  make init-db         - Initialize database and load POI data"
	@echo "  make reset-db        - Reset database and reload POI data"

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

load-data:
	@echo "📊 Loading POI data into database..."
	@if [ -f data/poi.json ]; then \
		$(DOCKER_COMPOSE) exec backend python scripts/load_pois.py; \
		echo ""; \
		echo "✅ POI data loaded successfully"; \
	else \
		echo "❌ Error: data/poi.json not found"; \
		exit 1; \
	fi

init-db: up
	@echo "⏳ Waiting for services to be ready..."
	@sleep 5
	@echo "📊 Initializing database and loading POI data..."
	@$(MAKE) load-data

reset-db: down
	@echo "🗑️  Resetting database..."
	$(DOCKER_COMPOSE) up -d db redis
	@sleep 3
	$(DOCKER_COMPOSE) up -d backend
	@sleep 5
	@echo "📊 Loading POI data..."
	@$(MAKE) load-data
	@echo "✅ Database reset complete"

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