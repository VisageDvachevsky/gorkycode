# 🧭 AI-Tourist

**Готовый к продакшену AI-помощник для пеших маршрутов по Нижнему Новгороду**

Генерирует персональные маршруты из 3–5 точек с ML-рекомендациями, объяснениями от LLM и интерактивной картой.

---

## 🏗 Архитектура

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│   React     │─────▶│   FastAPI    │─────▶│  PostgreSQL │
│  Фронтенд   │      │   Бэкенд     │      │  + Redis    │
└─────────────┘      └──────────────┘      └─────────────┘
                            │
                            ├──▶ Сервис эмбеддингов (sentence-transformers)
                            ├──▶ Ранжирование (косинусное сходство)
                            ├──▶ Планировщик маршрута (упрощённый TSP)
                            └──▶ LLM-сервис (Claude/GPT)
```

### Технологический стек

| Слой            | Технологии                                                   |
|-----------------|--------------------------------------------------------------|
| **Фронтенд**    | React 18 + TypeScript + Vite + Tailwind CSS + React-Leaflet |
| **Бэкенд**      | FastAPI + Python 3.11 + Poetry                               |
| **База данных** | PostgreSQL 16 + Redis 7                                      |
| **ML**          | sentence-transformers + scikit-learn + numpy                 |
| **LLM**         | Anthropic Claude Sonnet 4 / OpenAI GPT-4                     |
| **DevOps**      | Docker Compose + Makefile                                    |

---

## 🚀 Быстрый старт

### Требования

- Docker & Docker Compose
- API-ключи: Anthropic или OpenAI

### Установка

1. **Клонировать репозиторий**

```bash
git clone https://github.com/VisageDvachevsky/gorkycode
cd gorkycode
```

2. **Настроить окружение**

```bash
cp .env.example .env
# Укажите API-ключи:
# ANTHROPIC_API_KEY=sk-ant-...
# или
# OPENAI_API_KEY=sk-...
```

3. **Запустить все сервисы**

```bash
make up
```

Команда выполнит:

- Сборку Docker-образов
- Запуск PostgreSQL, Redis, Бэкенда, Фронтенда
- Инициализацию схемы БД
- Откроет приложение на `http://localhost:5173`

4. **Загрузить POI-данные**

```bash
docker compose exec backend poetry run python scripts/load_pois.py
```

### Команды разработки

```bash
make up           # Запуск всех сервисов
make down         # Остановка всех сервисов
make build        # Сборка контейнеров
make rebuild      # Пересборка и рестарт
make logs         # Общие логи
make logs-api     # Логи API
make clean        # Очистка volume и кэша
```

---

## 📂 Структура проекта

```
gorkycode/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── router.py
│   │   │       └── endpoints/
│   │   │           ├── embedding.py
│   │   │           └── route.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── models/
│   │   │   ├── poi.py
│   │   │   └── schemas.py
│   │   ├── services/
│   │   │   ├── embedding.py
│   │   │   ├── ranking.py
│   │   │   ├── route_planner.py
│   │   │   └── llm.py
│   │   └── main.py
│   ├── scripts/
│   │   └── load_pois.py
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   └── client.ts
│   │   ├── components/
│   │   │   ├── RouteForm.tsx
│   │   │   └── RouteDisplay.tsx
│   │   ├── types/
│   │   │   └── index.ts
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
├── data/
│   └── poi.json
├── docker-compose.yml
├── Makefile
└── README.md
```

---

## 🔌 API Endpoints

### `POST /api/v1/route/plan`

Генерация персонального пешего маршрута.

**Запрос:**

```json
{
  "interests": "street-art, panoramas, coffee",
  "hours": 3.0,
  "start_lat": 56.3287,
  "start_lon": 44.002,
  "social_mode": "solo",
  "coffee_preference": 90,
  "intensity": "medium"
}
```

**Ответ:**

```json
{
  "summary": "Интересное введение в маршрут",
  "route": [
    {
      "order": 1,
      "poi_id": 123,
      "name": "Площадь Минина",
      "lat": 56.3287,
      "lon": 44.002,
      "why": "Персональное объяснение",
      "tip": "Совет местного жителя",
      "est_visit_minutes": 20,
      "arrival_time": "2025-10-10T10:00:00Z",
      "leave_time": "2025-10-10T10:20:00Z",
      "is_coffee_break": false
    }
  ],
  "total_est_minutes": 180,
  "total_distance_km": 4.5,
  "notes": ["Альтернатива на дождливый день"],
  "atmospheric_description": "Поэтическое описание прогулки"
}
```

### `POST /api/v1/embedding/generate`

Генерация текстового эмбеддинга для кеширования.

---

## 🧠 ML-пайплайн

1. **Эмбеддинг пользовательского запроса** → `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
2. **Векторный поиск** → Косинусное сходство + корректировка по соц. режиму и интенсивности
3. **Оптимизация маршрута** → Жадный алгоритм ближайшего соседа с ограничением по времени
4. **Вставка кофейных точек** → Адаптивное добавление по предпочтениям пользователя
5. **LLM-объяснение** → LLM (ChatGPT / Claude Sonnet) генерирует персональные причины и советы

---

## 💎 Ключевые возможности

- ☕ **Адаптивные кофебрейки** — авто-вставка кафе по предпочтению
- 🎯 **Контекстное ранжирование** — учитывает соц. режим и интенсивность
- 🗺️ **Интерактивные карты** — визуализация на Leaflet
- ⚡ **Redis-кеширование** — быстрый доступ к эмбеддингам
- 📝 **Объяснения от LLM** — естественный язык для обоснования маршрута
- 🔄 **Реальное планирование** — под 2 секунды для эмбеддингов и ранжирования, <5 секунд на весь маршрут

---

## 🔧 Конфигурация

### Настройки бэкенда (`backend/app/core/config.py`)

- `EMBEDDING_MODEL` — модель sentence-transformers
- `LLM_PROVIDER` — "anthropic" или "openai"
- `LLM_MODEL` — модель для объяснений
- `DEFAULT_WALK_SPEED_KMH` — средняя скорость пешего движения

### Переменные окружения

См. `.env.example` для всех опций.

---

## 📊 Добавление новых POI

1. Редактируем `data/poi.json`:

```json
{
  "id": 9,
  "name": "Новое место",
  "lat": 56.xxx,
  "lon": 44.xxx,
  "category": "музей",
  "tags": ["искусство", "современное"],
  "description": "Описание на русском",
  "avg_visit_minutes": 45,
  "rating": 4.5
}
```

2. Перезагружаем данные:

```bash
docker compose exec backend poetry run python scripts/load_pois.py
```

---

## ☸️ Kubernetes Deployment (Production-Ready)

The application now supports production-grade Kubernetes deployment with microservices architecture and gRPC communication.

### Prerequisites

- Kubernetes cluster (minikube, k3s, or cloud provider)
- kubectl configured
- Helm 3.x installed

### Microservices Architecture

The application has been migrated to 7 microservices:

| Service | Port | Description |
|---------|------|-------------|
| **API Gateway** | 8000 | FastAPI gateway for HTTP requests |
| **Embedding Service** | 50051 | Sentence transformers for text embeddings |
| **Ranking Service** | 50052 | POI scoring and ranking |
| **Route Planner** | 50053 | TSP-based route optimization |
| **LLM Service** | 50054 | Claude/GPT explanations |
| **Geocoding Service** | 50055 | Address validation via 2GIS API |
| **POI Service** | 50056 | POI database and coffee shop search |

### Quick Start with Kubernetes

1. **Setup environment variables**

```bash
cp .env.example .env
# Fill in your API keys and database credentials
./scripts/env-to-yaml.sh  # Converts .env to Helm secrets
```

2. **Install with Helm**

```bash
make k8s-install  # Installs with one command
```

Or manually:

```bash
helm install ai-tourist ./helm/ai-tourist \
  --create-namespace \
  --namespace ai-tourist \
  --values .env.yaml
```

3. **Check deployment status**

```bash
kubectl get pods -n ai-tourist
kubectl get services -n ai-tourist
```

4. **Access the application**

Get the Minikube IP:

```bash
minikube service list -n ai-tourist
```

Open the frontend at `http://<MINIKUBE_IP>:<NODE_PORT>`

### Makefile Commands for Kubernetes

```bash
make k8s-install     # Install Helm chart
make k8s-deploy      # Deploy/upgrade application
make k8s-uninstall   # Remove deployment
make k8s-logs        # Show all pod logs
make k8s-status      # Check pod status
make proto-gen       # Generate gRPC proto files
make setup-check     # Verify cluster requirements
```

### Database Migrations

Database migrations run automatically via Helm hooks:

- Migration Job creates POI table schema
- Data Loader Job inserts initial POI data
- Jobs run on `post-install` and `post-upgrade`

### Monitoring & Observability

All services expose Prometheus metrics on port 9090:

- `/metrics` endpoint on each service
- Automatic scraping via annotations
- Grafana dashboards (optional)
- Jaeger tracing (optional)

### Configuration

Edit `helm/ai-tourist/values.yaml` to customize:

- Replica counts per service
- Resource limits (CPU/memory)
- Image tags and registries
- LLM provider (OpenAI vs Anthropic)
- Database persistence size

### Troubleshooting

**Pods not starting:**

```bash
kubectl describe pod <pod-name> -n ai-tourist
kubectl logs <pod-name> -n ai-tourist
```

**Database connection issues:**

```bash
kubectl exec -it postgres-0 -n ai-tourist -- psql -U aitourist -d aitourist_db
```

**gRPC communication errors:**

Check service discovery:

```bash
kubectl get svc -n ai-tourist
kubectl get endpoints -n ai-tourist
```

---

## 🧪 Тестирование

```bash
docker compose exec backend poetry run pytest
```

---

## 🎨 Разработка фронтенда

Работает на `http://localhost:5173` с включённой горячей перезагрузкой.

**Особенности:**

- Чистый минималистичный UI
- Адаптивный дизайн (под мобильные устройства)
- Валидация форм в реальном времени
- Интерактивные карты Leaflet
- Состояния загрузки и обработка ошибок
