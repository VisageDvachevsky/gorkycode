.PHONY: help up down build rebuild logs clean install-backend install-frontend test lint format

help:
	@echo "AI-Tourist Development Commands:"
	@echo "  make up              - Start all services"
	@echo "  make down            - Stop all services"
	@echo "  make build           - Build all containers"
	@echo "  make rebuild         - Rebuild and restart"
	@echo "  make logs            - Show logs (all services)"
	@echo "  make clean           - Remove volumes and containers"
	@echo "  make install-backend - Install backend dependencies"
	@echo "  make install-frontend- Install frontend dependencies"
	@echo "  make test            - Run tests"
	@echo "  make lint            - Run linters"
	@echo "  make format          - Format code"

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

rebuild: down build up

logs:
	docker compose logs -f

logs-api:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

clean:
	docker compose down -v
	rm -rf backend/__pycache__
	rm -rf backend/.pytest_cache
	find backend -type d -name "__pycache__" -exec rm -r {} +

install-backend:
	cd backend && poetry install

install-frontend:
	cd frontend && npm install

test:
	docker compose exec backend poetry run pytest

lint:
	docker compose exec backend poetry run ruff check app/
	docker compose exec backend poetry run mypy app/

format:
	docker compose exec backend poetry run black app/
	docker compose exec backend poetry run isort app/