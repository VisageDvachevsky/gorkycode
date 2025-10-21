# 🧭 AI-Tourist 2.0

**Многосервисный AI-помощник для пеших прогулок по Нижнему Новгороду**

Проект строит персональные маршруты на основе интересов, темпа прогулки и предпочтений по кофе, объясняет каждую остановку на естественном языке и показывает маршрут на интерактивной карте.

---

## ✨ Что умеет система
- Генерирует прогулки на 3–5 точек с учётом времени в пути и длительности посещений.
- Подмешивает кофе-точки и альтернативы в зависимости от настроек пользователя.
- Дает объяснения по каждой точке и общий нарратив прогулки через LLM (Claude / GPT).
- Покрывает все городские локации: достопримечательности, мемориалы, парки, арт-объекты.
- Предоставляет REST API и современный веб-фронтенд с картой Leaflet и подсказками в форме.

---

## 🏗 Архитектура платформы

```
┌─────────────┐        HTTP        ┌────────────────────────┐
│   React     │ ─────────────────▶ │   API Gateway (FastAPI)│
│  Frontend   │                    │ + Auth + Aggregation   │
└─────────────┘                    └────────────┬───────────┘
                                                │ gRPC
                 ┌──────────────────────────────┴─────────────────────────────┐
                 │            сервисная шина AI-Tourist                       │
                 │                                                             │
      ┌───────────────┐   ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
      │ Embedding     │   │ Ranking        │   │ Route Planner  │   │ LLM Service     │
      │ sentence-     │   │ feature scoring│   │ TSP heuristics │   │ Claude/GPT API  │
      │ transformers  │   └────────────────┘   └────────────────┘   └────────────────┘
                 │               │                    │                    │
                 └───────────────┴──────────────┬─────┴─────┬───────────────┘
                                                │           │
                                   ┌─────────────▼┐   ┌─────▼────────┐
                                   │ POI Service  │   │ Geocoding    │
                                   │ Postgres +   │   │ 2GIS adapter │
                                   │ Redis cache  │   └──────────────┘
                                   └─────┬────────┘
                                         │
                                   ┌─────▼────────┐
                                   │ PostgreSQL 16│
                                   │ Redis 7      │
                                   └──────────────┘
```

### Микросервисы
| Сервис | Технологии | Порт | Роль |
|--------|-------------|------|------|
| **Frontend** | React 18, TypeScript, Vite, Tailwind, React-Leaflet | 80 | SPA с формой предпочтений, картой и анимированными подсказками. |
| **API Gateway** | FastAPI, gRPC-клиенты, Prometheus metrics | 8000 (HTTP), 9090 (metrics) | Единая точка входа: REST API, авторизация, агрегирование ответов от gRPC-сервисов. |
| **Embedding Service** | Python 3.11, sentence-transformers, Redis cache | 50051 | Вычисляет мультиязычные текстовые эмбеддинги для запросов и POI. |
| **Ranking Service** | Python 3.11, NumPy, feature scoring | 50052 | Ранжирует кандидатные точки по косинусному сходству и городским эвристикам. |
| **Route Planner** | Python 3.11, networkx | 50053 | Решает ограниченную TSP-задачу, вставляет кофебрейки и проверяет тайминги. |
| **LLM Service** | Python 3.11, OpenAI/Anthropic SDK | 50054 | Генерирует описания маршрута, объяснения и советы. |
| **Geocoding Service** | Python 3.11, 2GIS API | 50055 | Валидирует координаты и адреса, нормализует стартовые точки. |
| **POI Service** | FastAPI + asyncpg, PostgreSQL, Redis | 50056 | Выдаёт POI, хранит метаданные и предоставляет gRPC/REST доступ. |
| **PostgreSQL + Redis** | Helm зависимость | 5432 / 6379 | Основное хранилище данных и кеш. |
| **Jobs** | Helm Jobs (db-migration, poi-loader) | — | Автоматическая миграция схемы и загрузка эталонных POI при деплое. |

### ML/AI пайплайн
1. **Нормализация запроса** → гейты API проверяют стартовую точку и таймбоксы.
2. **Генерация эмбеддинга** → `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` в embedding-service.
3. **Кандидаты POI** → POI-service отдаёт топ по тематике и радиусу, данные кешируются в Redis.
4. **Ранжирование** → scoring учитывает интересы, социальный режим, интенсивность и свежесть данных.
5. **Планировщик** → route-planner выбирает оптимальный порядок, вставляет кофейни и проверяет ограничения по времени.
6. **LLM-объяснения** → llm-service собирает маршрут в текст, генерирует атмосферу и советы.
7. **API-ответ** → gateway собирает финальную структуру и отдаёт фронту.

---

## 🧰 Инфраструктура и DevOps
- **Kubernetes (Minikube/Cloud)** — развёртывание через Helm-чарт `helm/ai-tourist` с шаблонами для всех сервисов, ingress, secret'ов и jobs.
- **Helm secrets & values** — конфигурации хранятся в `values.yaml`, приватные ключи подставляются через `scripts/env-to-yaml.sh` и `helm/ai-tourist/templates/secrets.yaml`.
- **Автоматические миграции** — `db-migration-job` создаёт схему БД, `poi-data-loader` загружает образцы или JSON из ConfigMap, оба job запускаются как Helm hooks.
- **Наблюдаемость** — каждый сервис экспонирует Prometheus-метрики на порту 9090, gateway добавляет `/metrics` через `prometheus_fastapi_instrumentator`.
- **Скрипты автоматизации** — каталог `scripts/` содержит генерацию proto, проверку окружения, проброс портов и загрузку данных.

---

## 📦 Структура репозитория
```
gorkycode/
├── frontend/                 # Vite-приложение (React + TypeScript)
├── services/                 # gRPC микросервисы (Python + Poetry)
│   ├── api-gateway/
│   ├── embedding-service/
│   ├── ranking-service/
│   ├── route-planner-service/
│   ├── llm-service/
│   ├── geocoding-service/
│   └── poi-service/
├── proto/                    # gRPC определения и резервные копии
├── helm/ai-tourist/          # Helm-чарт с deployments, services, jobs
├── k8s/                      # Отдельные YAML (postgres, redis, миграции)
├── scripts/                  # Утилиты: proto, портфорвардинг, загрузка POI
├── data/poi.json             # Исходные POI (используются ConfigMap'ом)
├── Makefile                  # Build, deploy, test команды для Minikube
├── old/backend/              # Архив монолитной реализации (для справки)
└── README.md
```

Каталог `old/backend` больше не участвует в сборке: он сохранён для изучения эволюции проекта.

---

## 🚀 Быстрый старт (Minikube + Helm)

### 1. Зависимости
- Docker с включённым BuildKit.
- Minikube ≥ 1.33, kubectl, Helm 3, Make, jq.
- Доступ к API-ключам: OpenAI *или* Anthropic, а также 2GIS для геокодинга.
- Проверить окружение можно командой `./scripts/setup-check.sh`.

### 2. Настройка переменных
```bash
cp .env.example .env
# заполните ключи: OPENAI_API_KEY / ANTHROPIC_API_KEY, TWOGIS_API_KEY, DB_PASSWORD и др.
./scripts/env-to-yaml.sh   # генерирует .env.yaml для подстановки в Helm
```

### 3. Запуск кластера и деплой
```bash
minikube start --cpus=6 --memory=12g
make all                 # build → deploy → test
# make show-url           # если запускали стадии по отдельности
```
Команда `make build` собирает образы в Docker окружении Minikube, `make deploy` включает ingress и накатывает Helm-чарт, `make test` прогоняет smoke-тесты через curl + jq внутри кластера.

### 4. Доступ к приложению
- Узнайте IP: `minikube ip` и пропишите в `/etc/hosts` строку `192.168.49.2 ai-tourist.local` (точное значение выводит `make show-url`).
- Откройте `http://ai-tourist.local` — фронт обслуживается через ingress.
- **WSL / Windows:**
  - Добавьте запись `192.168.49.2 ai-tourist.local` в файл `C:\Windows\System32\drivers\etc\hosts` (откройте редактор от имени администратора).
  - Если Windows не видит Minikube IP, запустите `make port-forward` внутри WSL и откройте `http://localhost:8080` (фронт) и `http://localhost:8000` (API). Скрипт пробрасывает порты на все интерфейсы и корректно завершает `kubectl port-forward` по Ctrl+C.
  - Git-конфигурация по умолчанию может конвертировать окончания строк; репозиторий уже включает `.gitattributes`, чтобы все shell-скрипты оставались в Unix-формате и запускались без ошибок `bash\r`.

### 5. Полезные команды
```bash
make status        # pods, services, ingress
make logs          # логи API gateway
make test          # smoke-тесты эндпоинтов внутри кластера
make clean         # удалить релиз и namespace
```

---

## 🛠 Локальная разработка
### Фронтенд
```bash
cd frontend
npm install
npm run dev -- --host
```
Vite запускает dev-сервер, который можно проксировать на backend через `.env` или локальный портфорвардинг. Бандл собирается `npm run build`.

### Python-сервисы
1. Установите Poetry 1.7+.
2. Для сервиса:
   ```bash
   cd services/api-gateway
   poetry install
   poetry run uvicorn app.main:app --reload --port 8000
   ```
3. Для gRPC сервисов используйте `poetry run python app/server.py` (имена серверов лежат в директориях `app/`).
4. Обновляйте протобуфы командой `./scripts/generate-protos.sh` — скрипт раскинет сгенерированный код по всем сервисам и поправит импорты.

### Тесты и проверка
- Интеграционные тесты: `make test` после деплоя.
- Юнит-тесты отдельных сервисов: `poetry run pytest` внутри нужного каталога.
- Lint фронтенда: `npm run lint`.

---

## 📊 Работа с POI-данными
- Основной файл — `data/poi.json`. Для обновления ConfigMap выполните `./scripts/generate-poi-configmap.sh` и затем `make deploy`/`helm upgrade` — job загрузит данные в PostgreSQL автоматически.
- Для ручной догрузки в существующий кластер используйте `./scripts/load-pois-to-k8s.sh` — скрипт сам установит портфорвард, прочитает пароль БД из секрета и прогонит загрузчик на Python.

---

## ❓ FAQ и советы
- **Ingress недоступен из Windows:** используйте `make port-forward` или встроенный `minikube tunnel`.
- **Не собираются образы:** убедитесь, что `eval $(minikube docker-env)` выполнен в вашей оболочке или используйте `make build`, который делает это сам.
- **LLM не отвечает:** проверьте значения `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` в секрете `ai-tourist-secrets` и логи `ai-tourist-llm-service`.

---

Счастливых прогулок по Нижнему Новгороду! 🏞
