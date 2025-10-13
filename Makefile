.PHONY: help proto build up down logs scale health test clean migrate backup restore

COMPOSE := docker compose
COMPOSE_PROD := docker compose -f docker-compose.yml -f docker-compose.prod.yml
PROTO_DIR := proto
SERVICES := gateway ml llm routing geocoding

help:
	@echo "🚀 AI-Tourist Microservices Management"
	@echo ""
	@echo "Development:"
	@echo "  make proto          Generate protobuf code for all services"
	@echo "  make build          Build all service images"
	@echo "  make up             Start all services (development)"
	@echo "  make down           Stop all services"
	@echo "  make restart        Restart all services"
	@echo "  make logs           Show logs (all services)"
	@echo "  make logs-<service> Show logs for specific service"
	@echo ""
	@echo "Production:"
	@echo "  make prod-up        Start in production mode"
	@echo "  make prod-down      Stop production deployment"
	@echo "  make prod-deploy    Full production deployment"
	@echo ""
	@echo "Scaling:"
	@echo "  make scale-gateway N=4    Scale API gateway to N instances"
	@echo "  make scale-workers N=8    Scale Celery workers to N instances"
	@echo ""
	@echo "Operations:"
	@echo "  make health         Check health of all services"
	@echo "  make test           Run integration tests"
	@echo "  make migrate        Run database migrations"
	@echo "  make backup         Backup PostgreSQL database"
	@echo "  make restore FILE=  Restore database from backup"
	@echo ""
	@echo "Maintenance:"
	@echo "  make clean          Remove containers, volumes, networks"
	@echo "  make clean-cache    Clear Redis cache"
	@echo "  make rebuild        Full rebuild and restart"

proto:
	@echo "📦 Generating protobuf code..."
	@for service in $(SERVICES); do \
		python -m grpc_tools.protoc \
			-I$(PROTO_DIR) \
			--python_out=services/$$service/app/proto \
			--grpc_python_out=services/$$service/app/proto \
			$(PROTO_DIR)/*.proto; \
		echo "✓ Generated proto for $$service"; \
	done

build:
	@echo "🔨 Building service images..."
	$(COMPOSE) build --parallel

up:
	@echo "🚀 Starting services..."
	$(COMPOSE) up -d
	@echo "⏳ Waiting for services to be healthy..."
	@sleep 5
	@make health

down:
	@echo "🛑 Stopping services..."
	$(COMPOSE) down

restart:
	@echo "🔄 Restarting services..."
	$(COMPOSE) restart

logs:
	$(COMPOSE) logs -f --tail=100

logs-gateway:
	$(COMPOSE) logs -f gateway-1 gateway-2

logs-ml:
	$(COMPOSE) logs -f ml-service

logs-llm:
	$(COMPOSE) logs -f llm-service

logs-routing:
	$(COMPOSE) logs -f routing-service

logs-workers:
	$(COMPOSE) logs -f celery-worker-1 celery-worker-2

prod-up:
	@echo "🚀 Starting production deployment..."
	$(COMPOSE_PROD) up -d
	@make health

prod-down:
	$(COMPOSE_PROD) down

prod-deploy:
	@echo "🚀 Full production deployment..."
	@make proto
	@make build
	@$(COMPOSE_PROD) pull
	@$(COMPOSE_PROD) up -d --remove-orphans
	@echo "⏳ Waiting for services..."
	@sleep 10
	@make health
	@echo "✅ Production deployment complete"

scale-gateway:
	@if [ -z "$(N)" ]; then echo "Usage: make scale-gateway N=4"; exit 1; fi
	@echo "⚖️  Scaling API Gateway to $(N) instances..."
	$(COMPOSE) up -d --scale gateway=$(N)

scale-workers:
	@if [ -z "$(N)" ]; then echo "Usage: make scale-workers N=8"; exit 1; fi
	@echo "⚖️  Scaling Celery workers to $(N) instances..."
	$(COMPOSE) up -d --scale celery-worker=$(N)

health:
	@echo "🏥 Checking service health..."
	@echo "\n=== API Gateway ==="
	@curl -sf http://localhost/health | jq . || echo "❌ Gateway unhealthy"
	@echo "\n=== ML Service ==="
	@docker exec aitourist-ml grpc_health_probe -addr=:50051 && echo "✅ ML Service healthy" || echo "❌ ML Service unhealthy"
	@echo "\n=== LLM Service ==="
	@docker exec aitourist-llm grpc_health_probe -addr=:50052 && echo "✅ LLM Service healthy" || echo "❌ LLM Service unhealthy"
	@echo "\n=== Routing Service ==="
	@docker exec aitourist-routing grpc_health_probe -addr=:50053 && echo "✅ Routing Service healthy" || echo "❌ Routing Service unhealthy"
	@echo "\n=== Geocoding Service ==="
	@docker exec aitourist-geocoding grpc_health_probe -addr=:50054 && echo "✅ Geocoding Service healthy" || echo "❌ Geocoding Service unhealthy"
	@echo "\n=== PostgreSQL ==="
	@docker exec aitourist-postgres pg_isready -U aitourist && echo "✅ PostgreSQL healthy" || echo "❌ PostgreSQL unhealthy"
	@echo "\n=== Redis ==="
	@docker exec aitourist-redis redis-cli ping && echo "✅ Redis healthy" || echo "❌ Redis unhealthy"

test:
	@echo "🧪 Running integration tests..."
	@pytest tests/integration -v --tb=short

migrate:
	@echo "🗄️  Running database migrations..."
	$(COMPOSE) exec gateway-1 alembic upgrade head

backup:
	@echo "💾 Creating database backup..."
	@mkdir -p backups
	@docker exec aitourist-postgres pg_dump -U aitourist aitourist_db | gzip > backups/backup_$$(date +%Y%m%d_%H%M%S).sql.gz
	@echo "✅ Backup created: backups/backup_$$(date +%Y%m%d_%H%M%S).sql.gz"

restore:
	@if [ -z "$(FILE)" ]; then echo "Usage: make restore FILE=backups/backup.sql.gz"; exit 1; fi
	@echo "📥 Restoring database from $(FILE)..."
	@gunzip -c $(FILE) | docker exec -i aitourist-postgres psql -U aitourist aitourist_db
	@echo "✅ Database restored"

clean:
	@echo "🧹 Cleaning up..."
	$(COMPOSE) down -v --remove-orphans
	@docker system prune -f
	@echo "✅ Cleanup complete"

clean-cache:
	@echo "🧹 Clearing Redis cache..."
	@docker exec aitourist-redis redis-cli FLUSHALL
	@echo "✅ Cache cleared"

rebuild:
	@echo "🔨 Full rebuild..."
	@make down
	@make build
	@make up
	@echo "✅ Rebuild complete"

watch:
	@echo "👀 Watching logs (Ctrl+C to stop)..."
	$(COMPOSE) logs -f

stats:
	@echo "📊 Service statistics..."
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

shell-gateway:
	$(COMPOSE) exec gateway-1 /bin/bash

shell-ml:
	$(COMPOSE) exec ml-service /bin/bash

shell-db:
	$(COMPOSE) exec postgres psql -U aitourist aitourist_db

shell-redis:
	$(COMPOSE) exec redis-master redis-cli