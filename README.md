# 🌍 AI-Tourist Нижний Новгород

**Production-ready AI-помощник для персональных пеших маршрутов с микросервисной архитектурой на Kubernetes**

[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.30+-326CE5?logo=kubernetes)](https://kubernetes.io/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18.3+-61DAFB?logo=react)](https://react.dev/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://www.python.org/)

Интеллектуальная система генерации туристических маршрутов с ML-рекомендациями, эмбеддингами предпочтений пользователя, объяснениями от LLM и оптимизацией маршрутов в реальном времени.

---

## 📋 Содержание

- [Ключевые возможности](#-ключевые-возможности)
- [Архитектура](#-архитектура)
- [Технологический стек](#-технологический-стек)
- [Быстрый старт](#-быстрый-старт)
- [Kubernetes Deployment](#-kubernetes-deployment)
- [Микросервисы](#-микросервисы)
- [Мониторинг и метрики](#-мониторинг-и-метрики)
- [API Reference](#-api-reference)
- [Разработка](#-разработка)
- [Production Checklist](#-production-checklist)

---

## 🎯 Ключевые возможности

### Для пользователя
- 🗺️ **Персональные маршруты** — генерация на основе интересов и предпочтений
- ☕ **Умные кофебрейки** — автоматическая вставка кафе по расписанию и предпочтениям
- 🎨 **Контекстная адаптация** — учет социального режима (solo/группа) и интенсивности прогулки
- 💬 **AI-объяснения** — естественноязычные пояснения выбора каждой точки от Claude/GPT
- 📍 **Интерактивная карта** — визуализация маршрута с временными метками
- ⚡ **Мгновенный отклик** — генерация маршрута за 2-5 секунд

### Для разработчика
- 🏗️ **Микросервисная архитектура** — 5 независимых gRPC-сервисов
- ☸️ **Kubernetes-native** — production-ready deployment с автомасштабированием
- 📊 **Observability** — Prometheus метрики + Grafana дашборды
- 🔒 **Security** — Network Policies, RBAC, секреты в Kubernetes Secrets
- 🚀 **High Availability** — HPA, Pod Disruption Budgets, health checks
- 🐳 **One-command deploy** — `make k8s-apply`

---

## 🏗 Архитектура

### Общая схема

```
┌─────────────────────────────────────────────────────────────────┐
│                         Kubernetes Cluster                       │
│                                                                   │
│  ┌───────────────┐    ┌────────────────────────────────────┐   │
│  │   Frontend    │    │         Gateway (FastAPI)          │   │
│  │   (React)     │◄───┤    HPA: 2-4 replicas              │   │
│  │   2 replicas  │    │    Port: 8000                      │   │
│  └───────────────┘    └────────────────────────────────────┘   │
│                                    │                             │
│                         ┌──────────┼──────────┐                 │
│                         ▼          ▼          ▼                 │
│       ┌─────────────────────────────────────────────────┐       │
│       │            gRPC Microservices                    │       │
│       │                                                  │       │
│       │  ┌────────────┐  ┌────────────┐  ┌──────────┐  │       │
│       │  │ML Service  │  │LLM Service │  │ Routing  │  │       │
│       │  │:50051      │  │:50052      │  │ :50053   │  │       │
│       │  │Embeddings  │  │Claude/GPT  │  │ TSP opt  │  │       │
│       │  │HPA: 1-3    │  │2 replicas  │  │1 replica │  │       │
│       │  └────────────┘  └────────────┘  └──────────┘  │       │
│       │                                                  │       │
│       │  ┌────────────┐                                 │       │
│       │  │ Geocoding  │                                 │       │
│       │  │ :50054     │                                 │       │
│       │  │ 2GIS API   │                                 │       │
│       │  │ 1 replica  │                                 │       │
│       │  └────────────┘                                 │       │
│       └─────────────────────────────────────────────────┘       │
│                         │          │                             │
│                         ▼          ▼                             │
│       ┌────────────────────────────────────────┐                │
│       │  PostgreSQL      Redis      Prometheus │                │
│       │  (Persistent)  (Persistent)  + Grafana │                │
│       └────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────────┘
```

### ML Pipeline

```
User Request → Embedding Generation → Vector Search → Route Optimization
     ↓                  ↓                    ↓                ↓
  Interests     sentence-transformers    Cosine         Greedy TSP
   Tags           (384-dim vectors)      Similarity    + Time constraints
   Prefs                                                      ↓
                                                     Coffee Break Insertion
                                                              ↓
                                                     LLM Explanation Generation
                                                              ↓
                                                     Route with Rich Context
```

---

## 🛠 Технологический стек

### Backend & Services

| Компонент | Технологии | Назначение |
|-----------|------------|-----------|
| **Gateway** | FastAPI + Python 3.11 + Poetry | Orchestration, REST API, gRPC clients |
| **ML Service** | sentence-transformers + torch | Эмбеддинги текста (384-dim vectors) |
| **LLM Service** | Anthropic Claude / OpenAI | Генерация объяснений маршрута |
| **Routing Service** | NumPy + scikit-learn | Оптимизация TSP + косинусное сходство |
| **Geocoding Service** | 2GIS API + httpx | Геокодирование адресов и POI |

### Infrastructure

| Слой | Технологии |
|------|------------|
| **Orchestration** | Kubernetes 1.30+, Minikube |
| **Container Runtime** | Docker 24+ |
| **Service Mesh** | gRPC (Protocol Buffers) |
| **Databases** | PostgreSQL 16 + Redis 7 |
| **Monitoring** | Prometheus + Grafana |
| **Autoscaling** | Horizontal Pod Autoscaler (HPA) |
| **Security** | Network Policies, RBAC, Secrets |
| **CI/CD** | Makefile automation |

### Frontend

| Layer | Tech |
|-------|------|
| **Framework** | React 18 + TypeScript + Vite |
| **Styling** | Tailwind CSS |
| **Maps** | React-Leaflet + OpenStreetMap |
| **State** | React Hooks (useState, useEffect) |
| **HTTP Client** | Fetch API |

---

## 🚀 Быстрый старт

### Системные требования

- **CPU**: 4+ cores (8 recommended)
- **RAM**: 8GB+ (16GB recommended)
- **Disk**: 20GB+ свободного места
- **OS**: Linux, macOS, Windows (WSL2)

### Предварительная установка

```bash
# Kubernetes (Minikube)
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install kubectl /usr/local/bin/kubectl
```

### Deployment за 3 шага

```bash
# 1. Клонировать репозиторий
git clone https://github.com/VisageDvachevsky/gorkycode
cd gorkycode

# 2. Настроить окружение
cp .env.example .env
# Отредактируй .env и добавь API ключи:
# ANTHROPIC_API_KEY=sk-ant-...
# или OPENAI_API_KEY=sk-...
# TWOGIS_API_KEY=...

# 3. Запустить кластер и задеплоить
minikube start --cpus=4 --memory=8192
make k8s-apply

# Подожди 2-3 минуты пока все поды запустятся
kubectl get pods -n aitourist --watch
```

### Доступ к сервисам

```bash
# Port forwarding
make k8s-port

# Или вручную:
kubectl port-forward -n aitourist svc/gateway 8000:8000 &
kubectl port-forward -n aitourist svc/frontend 3000:80 &
kubectl port-forward -n aitourist svc/grafana 3001:3000 &
```

Открой в браузере:
- **API Documentation**: http://localhost:8000/docs
- **Frontend App**: http://localhost:3000
- **Grafana Monitoring**: http://localhost:3001

---

## ☸️ Kubernetes Deployment

### Структура манифестов

```
k8s/
├── 00-namespace.yaml           # Namespace aitourist
├── 01-configmap.yaml           # Конфигурация приложения
├── 02-secrets.yaml             # Секреты (генерируется автоматически)
├── 03-pvc.yaml                 # Persistent Volume Claims
├── 04-db-init.yaml             # Init скрипты БД
├── 05-network-policy.yaml      # Сетевые политики безопасности
├── 06-pod-disruption-budget.yaml # PDB для HA
├── 07-rbac.yaml                # Service Accounts & Roles
├── 10-postgres.yaml            # PostgreSQL Deployment
├── 11-redis.yaml               # Redis Deployment
├── 12-ml-service.yaml          # ML Service + HPA
├── 13-gateway.yaml             # Gateway API + HPA
├── 14-frontend.yaml            # React Frontend
├── 15-llm-service.yaml         # LLM Service
├── 16-routing-service.yaml     # Routing Service
├── 17-geocoding-service.yaml   # Geocoding Service
├── 20-ingress.yaml             # Ingress Controller
├── 30-monitoring.yaml          # Prometheus + Grafana
├── 31-servicemonitor.yaml      # ServiceMonitors (опционально)
└── 40-backup.yaml              # Backup CronJob
```

### Resource Allocation

| Service | CPU Request | CPU Limit | Memory Request | Memory Limit | Replicas |
|---------|------------|-----------|----------------|--------------|----------|
| Gateway | 100m | 1000m | 128Mi | 512Mi | 2-4 (HPA) |
| ML Service | 200m | 2000m | 512Mi | 2Gi | 1-3 (HPA) |
| LLM Service | 100m | 500m | 128Mi | 512Mi | 2 |
| Routing | 100m | 500m | 128Mi | 256Mi | 1 |
| Geocoding | 100m | 500m | 128Mi | 256Mi | 1 |
| PostgreSQL | 250m | 1000m | 256Mi | 1Gi | 1 |
| Redis | 100m | 500m | 64Mi | 256Mi | 1 |
| Frontend | 50m | 200m | 32Mi | 128Mi | 2 |

**Total cluster requirements:**
- CPU: ~1000m (1 core) at idle, ~4000m (4 cores) under load
- Memory: ~2.5Gi at idle, ~6Gi under load

### Автомасштабирование (HPA)

**Gateway HPA:**
```yaml
minReplicas: 2
maxReplicas: 4
metrics:
  - CPU: 70%
  - Memory: 85%
```

**ML Service HPA:**
```yaml
minReplicas: 1
maxReplicas: 3
metrics:
  - CPU: 70%
  - Memory: 80%
```

### High Availability Features

- ✅ **Pod Disruption Budgets** — минимум 1 под всегда доступен
- ✅ **Health Checks** — liveness & readiness probes
- ✅ **Anti-affinity** — распределение подов по узлам
- ✅ **Persistent Storage** — PVC для PostgreSQL и Redis
- ✅ **Network Policies** — изоляция сетевого трафика
- ✅ **RBAC** — ограниченные права Service Accounts

### Мониторинг и логирование

```bash
# Статус всех ресурсов
make k8s-status

# Логи конкретного сервиса
make k8s-logs          # Gateway
make k8s-logs-ml       # ML Service
make k8s-logs-all      # Все сервисы

# Метрики ресурсов
kubectl top nodes
kubectl top pods -n aitourist

# Доступ к Grafana
kubectl port-forward -n aitourist svc/grafana 3001:3000
# http://localhost:3001 (admin/[GRAFANA_PASSWORD])
```

---

## 🔬 Микросервисы

### Gateway (FastAPI)

**Endpoint:** `http://gateway:8000`

**Responsibilities:**
- REST API для клиентов
- Оркестрация gRPC-вызовов
- Валидация входных данных
- Агрегация ответов микросервисов
- Database operations (PostgreSQL)
- Cache management (Redis)

**gRPC Clients:**
```python
ml_client → ML Service (embeddings)
llm_client → LLM Service (explanations)
routing_client → Routing Service (TSP)
geocoding_client → Geocoding Service (2GIS)
```

### ML Service

**Endpoint:** `grpc://ml-service:50051`

**Responsibilities:**
- Генерация text embeddings (384-dim)
- Модель: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- Кеширование эмбеддингов в Redis
- Batch processing поддержка
- Косинусное сходство для векторов

**Proto:**
```protobuf
service EmbeddingService {
  rpc GenerateEmbedding(EmbeddingRequest) returns (EmbeddingResponse);
  rpc GenerateEmbeddingBatch(EmbeddingBatchRequest) returns (EmbeddingBatchResponse);
  rpc CosineSimilarity(SimilarityRequest) returns (SimilarityResponse);
  rpc HealthCheck(HealthCheckRequest) returns (HealthCheckResponse);
}
```

### LLM Service

**Endpoint:** `grpc://llm-service:50052`

**Responsibilities:**
- Генерация контекстных объяснений маршрута
- Поддержка Anthropic Claude & OpenAI GPT
- Промпты для туристических рекомендаций
- Асинхронная обработка (опционально)
- Retry logic с exponential backoff

**Features:**
- Atmospheric descriptions
- Per-POI reasoning ("почему именно эта точка?")
- Local tips and recommendations
- Alternative suggestions

### Routing Service

**Endpoint:** `grpc://routing-service:50053`

**Responsibilities:**
- Оптимизация порядка точек (Greedy TSP)
- Расчет времени прохождения
- Учет walking speed
- Вставка кофебрейков
- Distance matrix calculation

**Algorithm:**
```
1. Start from user location
2. Greedy nearest neighbor selection
3. Time constraint validation
4. Coffee break insertion (based on preference)
5. Final route with timestamps
```

### Geocoding Service

**Endpoint:** `grpc://geocoding-service:50054`

**Responsibilities:**
- Геокодирование адресов (2GIS API)
- Reverse geocoding
- POI search
- Distance calculation
- Rate limiting & caching

---

## 📊 Мониторинг и метрики

### Prometheus Metrics

**Доступные метрики:**
```
# HTTP метрики
http_requests_total
http_request_duration_seconds
http_requests_in_progress

# gRPC метрики
grpc_server_handled_total
grpc_server_handling_seconds

# Custom метрики
route_generation_duration_seconds
embedding_cache_hit_ratio
llm_api_calls_total
```

### Grafana Dashboards

**Pre-configured:**
- Gateway API Performance
- ML Service Embeddings Stats
- Database Connection Pool
- Redis Cache Performance
- Pod Resource Usage
- HPA Scaling Events

**Access:**
```bash
kubectl port-forward -n aitourist svc/grafana 3001:3000
# Login: admin / [GRAFANA_PASSWORD from secrets]
```

---

## 🔌 API Reference

### POST `/api/v1/route/plan`

Генерация персонализированного маршрута.

**Request:**
```json
{
  "interests": "street-art, history, panoramas",
  "hours": 3.5,
  "start_lat": 56.3287,
  "start_lon": 44.002,
  "social_mode": "solo",
  "coffee_preference": 80,
  "intensity": "medium"
}
```

**Response:**
```json
{
  "summary": "Интеллектуальное введение в ваш маршрут",
  "route": [
    {
      "order": 1,
      "poi_id": 5,
      "name": "Площадь Минина и Пожарского",
      "lat": 56.3287,
      "lon": 44.002,
      "category": "landmark",
      "tags": ["history", "architecture"],
      "why": "Сердце Нижнего Новгорода с богатой историей...",
      "tip": "Приходите на рассвете для лучших фото",
      "est_visit_minutes": 20,
      "arrival_time": "2025-10-15T10:00:00Z",
      "leave_time": "2025-10-15T10:20:00Z",
      "is_coffee_break": false
    },
    {
      "order": 2,
      "poi_id": 42,
      "name": "Coffee Bean",
      "is_coffee_break": true,
      "est_visit_minutes": 15
    }
  ],
  "total_est_minutes": 210,
  "total_distance_km": 4.8,
  "atmospheric_description": "Эмоциональное описание прогулки...",
  "notes": ["Альтернатива: Музей на дождливый день"]
}
```

**Параметры:**

| Параметр | Тип | Описание | По умолчанию |
|----------|-----|----------|--------------|
| `interests` | string | Интересы через запятую | required |
| `hours` | float | Желаемая длительность | 2.0-8.0 |
| `start_lat` | float | Широта старта | required |
| `start_lon` | float | Долгота старта | required |
| `social_mode` | enum | "solo" / "group" | "solo" |
| `coffee_preference` | int | 0-100 (частота брейков) | 50 |
| `intensity` | enum | "low" / "medium" / "high" | "medium" |

---

## 💻 Разработка

### Makefile Commands

```bash
# Kubernetes Operations
make k8s-apply          # Deploy to cluster
make k8s-delete         # Delete all resources
make k8s-status         # Check pods/services status
make k8s-restart        # Restart all deployments
make k8s-port           # Port forward (auto-cleanup)
make k8s-port-stop      # Stop port forwarding

# Logs & Debugging
make k8s-logs           # Gateway logs
make k8s-logs-ml        # ML Service logs
make k8s-logs-all       # All services logs
make k8s-shell-gateway  # Exec into Gateway pod
make k8s-shell-ml       # Exec into ML pod

# Build & Push
make build              # Build Docker images
make k8s-build          # Build for Kubernetes

# Cleanup
make clean              # Remove build artifacts
make k8s-delete         # Delete k8s namespace
```

### Local Development (Docker Compose)

```bash
# Для разработки без Kubernetes
make dev-up             # Start dev environment
make dev-down           # Stop dev environment
make dev-logs           # View logs

# Или напрямую:
docker-compose up -d
docker-compose logs -f
```

### Добавление новых POI

1. Редактируй `data/poi.json`:
```json
{
  "id": 99,
  "name": "Новая точка интереса",
  "lat": 56.xxx,
  "lon": 44.xxx,
  "category": "museum",
  "tags": ["art", "modern"],
  "description": "Полное описание места",
  "avg_visit_minutes": 45,
  "rating": 4.7
}
```

2. Загрузи в БД:
```bash
kubectl exec -it -n aitourist deployment/gateway -- \
  poetry run python scripts/load_pois.py
```

### Тестирование

```bash
# Unit tests
kubectl exec -it -n aitourist deployment/gateway -- \
  poetry run pytest tests/

# API tests
curl -X POST http://localhost:8000/api/v1/route/plan \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/sample_request.json
```

---

## ✅ Production Checklist

### Security

- [ ] Все секреты в Kubernetes Secrets (не в git!)
- [ ] Network Policies настроены
- [ ] RBAC с минимальными правами
- [ ] TLS для Ingress (если используется)
- [ ] Database credentials ротация
- [ ] API rate limiting

### Reliability

- [ ] HPA настроен и протестирован
- [ ] PDB для критичных сервисов
- [ ] Health checks work
- [ ] Persistent storage для БД
- [ ] Backup CronJob активен
- [ ] Graceful shutdown handling

### Monitoring

- [ ] Prometheus scraping работает
- [ ] Grafana dashboards настроены
- [ ] Alerts configured (опционально)
- [ ] Logs aggregation (опционально: ELK/Loki)
- [ ] Distributed tracing (опционально: Jaeger)

### Performance

- [ ] Resource limits установлены
- [ ] Redis caching работает
- [ ] Database indexes оптимизированы
- [ ] Connection pooling настроен
- [ ] ML model preloaded при старте

### CI/CD (Recommended)

- [ ] GitHub Actions / GitLab CI
- [ ] Automated tests
- [ ] Docker registry (DockerHub/GCR/ECR)
- [ ] Helm charts (опционально)
- [ ] Canary deployments

---

## 🐛 Troubleshooting

### Pods не запускаются

```bash
# Проверь события
kubectl describe pod -n aitourist <pod-name>

# Проверь логи
kubectl logs -n aitourist <pod-name>

# Проверь ресурсы кластера
kubectl top nodes
kubectl describe nodes
```

### ML Service падает

**Возможные причины:**
- Недостаточно памяти (нужно 2Gi limit)
- Модель не загружена
- Проблемы с protobuf версией

```bash
# Проверь логи
kubectl logs -n aitourist -l app=ml-service --tail=50

# Увеличь memory limit
kubectl patch deployment ml-service -n aitourist \
  -p '{"spec":{"template":{"spec":{"containers":[{"name":"ml-service","resources":{"limits":{"memory":"3Gi"}}}]}}}}'
```

### Gateway не коннектится к gRPC сервисам

```bash
# Проверь service endpoints
kubectl get endpoints -n aitourist

# Проверь network policies
kubectl get networkpolicies -n aitourist

# Test connection from Gateway pod
kubectl exec -it -n aitourist deployment/gateway -- \
  nc -zv ml-service 50051
```

### Высокое потребление памяти

```bash
# Проверь HPA статус
kubectl get hpa -n aitourist

# Уменьши max replicas если нужно
kubectl patch hpa gateway-hpa -n aitourist \
  -p '{"spec":{"maxReplicas":3}}'

# Или увеличь кластер
minikube stop
minikube delete
minikube start --cpus=6 --memory=12288
```

---

## 📚 Дополнительные ресурсы

- **Kubernetes Docs**: https://kubernetes.io/docs/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Sentence Transformers**: https://sbert.net/
- **Anthropic Claude**: https://docs.anthropic.com/
- **Prometheus**: https://prometheus.io/docs/

---

## 👥 Contributing

Pull requests приветствуются! Для major changes создайте issue для обсуждения.

**Development workflow:**
1. Fork репозиторий
2. Создай feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Открой Pull Request

---

## 🎓 Credits

Developed by **Visage Dvachevsky** для хакатона GorkyCode 2025

**Special thanks:**
- Anthropic Claude & OpenAI ChatGPT для LLM capabilities
- Sentence Transformers community
- Kubernetes contributors
- Нижний Новгород за вдохновение 🏛️

---
