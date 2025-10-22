# 🧭 AI-Tourist 2.0

**Многосервисный AI-помощник для пеших прогулок по Нижнему Новгороду**

Проект строит персональные маршруты на основе интересов, темпа прогулки и предпочтений по кофе, объясняет каждую остановку, показывает маршрут на интерактивной карте и позволяет делиться им с друзьями.

---

## ✨ Возможности
- Персональные прогулки на 3–6 точек с учётом времени на переходы и посещения.
- Умное ранжирование кандидатов по интересам, социальному режиму, погоде и рейтингу.
- Автоматическое добавление кофе-брейков и проверка расписаний (время открытия/закрытия).
- Генерация описаний маршрута и советов через LLM с fallback-ответами при отсутствии ключей.
- Современный веб-фронтенд (React + Leaflet) с визуализацией маршрута и подсказками в форме.
- REST API, Prometheus-метрики и gRPC-взаимодействие между сервисами.

---

## 🏗 Архитектура платформы
```
┌─────────────┐        HTTP        ┌────────────────────────┐
│   React     │ ─────────────────▶ │   API Gateway (FastAPI)│
│  Frontend   │                    │ + Auth + Aggregation   │
└─────────────┘                    └────────────┬───────────┘
                                                │ gRPC
                 ┌──────────────────────────────┴────────────────────────────┐
                 │                    сервисная шина AI-Tourist              │
                 │                                                            │
      ┌───────────────┐   ┌────────────────┐   ┌────────────────┐   ┌────────────────┐
      │ Embedding     │   │ Ranking        │   │ Route Planner  │   │ LLM Service     │
      │ sentence-     │   │ feature scoring│   │ heuristics     │   │ Claude/OpenAI   │
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
                                   └─────────────┘
```

### Микросервисы
| Сервис | Технологии | Порт | Роль |
|--------|-------------|------|------|
| **Frontend** | React 18, TypeScript, Vite, Tailwind, React-Leaflet | 5173 | SPA с формой предпочтений, картой и подсказками. |
| **API Gateway** | FastAPI, gRPC-клиенты, Prometheus metrics | 8000 (HTTP), 9090 (metrics) | REST API, агрегирование ответов от gRPC-сервисов, health-check. |
| **Embedding Service** | Python 3.11, sentence-transformers, Redis cache | 50051 | Векторизует запросы и описания POI, кеширует результаты. |
| **Ranking Service** | Python 3.11, NumPy, SQLAlchemy | 50052 | Ранжирует кандидатов по семантике, качеству, популярности и контексту. |
| **Route Planner** | Python 3.11, networkx, Redis | 50053 | Собирает маршрут, учитывает расписания, темп и буферы безопасности. |
| **LLM Service** | Python 3.11, OpenAI/Anthropic SDK | 50054 | Генерирует объяснения и заметки, поддерживает fallback-ответы без ключей. |
| **Geocoding Service** | Python 3.11, 2GIS API | 50055 | Валидирует координаты и нормализует адреса. |
| **POI Service** | FastAPI gRPC, SQLAlchemy, PostgreSQL | 50056 | Хранит точки интереса, отдаёт списки и категории, ищет кафе. |
| **PostgreSQL + Redis** | Docker/Helm зависимости | 5432 / 6379 | Хранилище POI и кеш маршрутизатора/эмбеддингов. |
| **POI Loader (job)** | Python скрипт | — | Однократная загрузка POI и эмбеддингов из `data/poi.json`. |

---

## 🧰 Подготовка окружения (Docker, kubectl, Minikube, Helm)
Эти шаги помогут развернуть весь стек даже на чистой машине. В большинстве случаев будет достаточно выполнения команд ниже в WSL2, macOS или Linux. Для Windows рекомендуем использовать WSL2 (Ubuntu).

### Требования к машине
- 4 CPU и 12 ГБ RAM (8 ГБ минимум, но тогда увеличьте swap в Minikube).
- 20 ГБ свободного места на диске под образы и тома.
- Включённая аппаратная виртуализация (BIOS/UEFI: Intel VT-x / AMD-V).

### 1. Установка Docker
- **macOS**: [Docker Desktop](https://www.docker.com/products/docker-desktop/).
- **Windows 11**: [Docker Desktop](https://www.docker.com/products/docker-desktop/) + WSL2 backend (при установке поставьте галочку «Use WSL2»).
- **Ubuntu / Debian**:
  ```bash
  sudo apt-get update
  sudo apt-get install -y ca-certificates curl gnupg lsb-release
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/$(. /etc/os-release && echo "$ID")/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  echo \
    "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/$(. /etc/os-release && echo "$ID") \
    $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
  sudo usermod -aG docker "$USER"  # чтобы запускать без sudo, relogin после команды
  ```

### 2. kubectl
- **macOS**:
  ```bash
  brew install kubectl
  ```
- **Windows (PowerShell)**:
  ```powershell
  winget install --id Kubernetes.kubectl --source winget
  ```
- **Ubuntu / Debian**:
  ```bash
  sudo apt-get update
  sudo apt-get install -y apt-transport-https ca-certificates curl
  sudo curl -fsSLo /usr/share/keyrings/kubernetes-archive-keyring.gpg https://packages.cloud.google.com/apt/doc/apt-key.gpg
  echo "deb [signed-by=/usr/share/keyrings/kubernetes-archive-keyring.gpg] https://apt.kubernetes.io/ kubernetes-xenial main" | \
    sudo tee /etc/apt/sources.list.d/kubernetes.list
  sudo apt-get update
  sudo apt-get install -y kubectl
  ```

### 3. Minikube
- **macOS**:
  ```bash
  brew install minikube
  ```
- **Windows (PowerShell)**:
  ```powershell
  winget install --id Kubernetes.minikube --source winget
  ```
- **Ubuntu / Debian**:
  ```bash
  curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
  sudo install minikube-linux-amd64 /usr/local/bin/minikube
  ```
- После установки запустите `minikube config set driver docker`, чтобы использовать Docker как драйвер виртуализации (работает в WSL2 и на Linux/macOS с Docker Desktop).

### 4. Helm
- **macOS**:
  ```bash
  brew install helm
  ```
- **Windows (PowerShell)**:
  ```powershell
  winget install --id Kubernetes.Helm --source winget
  ```
- **Ubuntu / Debian**:
  ```bash
  curl https://baltocdn.com/helm/signing.asc | sudo apt-key add -
  sudo apt-get install -y apt-transport-https --no-install-recommends
  echo "deb https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
  sudo apt-get update
  sudo apt-get install -y helm
  ```

### 5. Make, jq и утилиты
- **macOS**: входят в Xcode Command Line Tools (`xcode-select --install`).
- **Windows (WSL)**: `sudo apt-get install -y make jq` внутри WSL.
- **Linux**: `sudo apt-get install -y make jq` (или `yay -S make jq` на Arch).

После установки зависимостей проверьте окружение:
```bash
./scripts/setup-check.sh
```
Скрипт подтвердит наличие Docker, kubectl, Helm и Minikube, а также покажет версию драйвера.

---

## 📦 Структура репозитория
```
gorkycode/
├── data/                     # Источники POI, конфиг для загрузчика
├── docker-compose.yml        # Локальный запуск без Kubernetes
├── docs/                     # ADR и дополнительная документация
├── frontend/                 # Vite-приложение (React + TypeScript)
├── helm/ai-tourist/          # Helm-чарт для Minikube/кластера
├── k8s/                      # Дополнительные YAML-манифесты
├── proto/                    # gRPC определения
├── scripts/                  # Утилиты: генерация proto, загрузка POI
├── services/
│   ├── api-gateway/
│   ├── embedding-service/
│   ├── geocoding-service/
│   ├── llm-service/
│   ├── poi-service/
│   ├── ranking-service/
│   ├── route-planner-service/
│   └── python-common/        # Общая библиотека (логирование, health, interceptors)
└── old/                      # Архив монолитной реализации (не используется)
```

---

## 🚀 Быстрый старт (Minikube + Helm)
Основной способ развернуть проект — локальный кластер Kubernetes на Minikube. Гайд ниже покрывает полный цикл: от подготовки переменных до smoke-тестов.

### 1. Подготовить переменные окружения
```bash
cp .env.example .env
# укажите ключи в .env (OpenAI/Anthropic, 2GIS, настройки БД)
./scripts/env-to-yaml.sh   # конвертирует .env в helm/values.yaml и .env.yaml
.scripts/validate-env-yaml.sh # валилирует secrets.yaml 
```
Скрипт создаст файл `helm/ai-tourist/values.yaml`, который Helm подключает как Kubernetes Secret.

### 2. Запустить Minikube с нужными ресурсами
```bash
minikube start --driver=docker --cpus=6 --memory=12g --disk-size=40g
minikube addons enable ingress
minikube addons enable metrics-server
```
Если ресурсов меньше (например, ноутбук на 16 ГБ), можно снизить параметры до `--cpus=4 --memory=8192`. Главное — оставить запас по памяти для Docker образов.

### 3. Собрать образы внутри кластера и задеплоить
```bash
make all
```
Цель `make all` выполнит три шага: `make build` (сборка образов в Docker окружении Minikube), `make deploy` (установка Helm-чарта с ingress) и `make test` (curl smoke-тесты внутри кластера). В логах появятся подсказки по статусу подов и доступу.

> 💡 Для повторного деплоя без пересборки образов используйте `make deploy`. Если нужно только пересобрать код после правок — `make build`.

### 4. Получить URL и открыть приложение
```bash
make show-url
```
Команда выведет IP Minikube, строчку для `/etc/hosts` (`<ip> ai-tourist.local`) и альтернативу через `kubectl port-forward`. На Windows/WSL используйте `make port-forward`, чтобы отдать фронтенд и API на `localhost` хостовой системы.

### 5. Проверить состояние кластера
```bash
make status   # pod'ы, сервисы и ingress
make logs     # последние логи API Gateway
kubectl get pods -n ai-tourist
```
Дополнительно можно открыть dashboard: `minikube dashboard` (запустит web UI в браузере).

### 6. Обновление данных и повторный запуск
- Hook-job в chart автоматически запускает загрузчик POI при каждом деплое. Для ручного перезапуска выполните: `kubectl delete job -n ai-tourist -l job-name=ai-tourist-poi-loader` — Helm пересоздаст job.
- Очистить окружение можно командой `make clean`. Это удалит namespace и Helm release, но оставит кластер Minikube.

### 7. Остановка кластера
```bash
minikube stop
```
Чтобы полностью удалить виртуальную машину и образы — `minikube delete`.

---

## 🔁 Альтернатива: Docker Compose (без Kubernetes)
Если времени на установку Minikube совсем нет, можно поднять сервисы напрямую через Docker Compose. Этот режим пригодится для быстрых демо, но в нём нет ingress, hooks и Kubernetes-обвязки.

### 1. Предварительная настройка
- Установите Docker Desktop / Docker Engine и убедитесь, что доступна команда `docker compose` (v2).
- Скопируйте переменные и заполните ключи:
  ```bash
  cp .env.example .env
  # при необходимости укажите API-ключи
  ```

### 2. Запуск сервисов
```bash
docker compose up --build -d postgres redis embedding-service ranking-service route-planner-service poi-service geocoding-service llm-service api-gateway frontend
```
Логи доступны через `docker compose logs -f <service>`. При первом запуске потребуется чуть больше времени из-за сборки образов.

### 3. Загрузка данных POI
```bash
docker compose run --rm poi-loader
```
Скрипт создаст схему БД и посчитает эмбеддинги. Повторный запуск безопасен — данные будут обновлены.

### 4. Доступ к сервисам
- API: `http://localhost:8000` (`/docs`, `/healthz`, `/api/v1/routes/plan`).
- Метрики: `http://localhost:9090/metrics`.
- Фронтенд: `http://localhost:5173`.

Остановить окружение: `docker compose down`. Чтобы удалить volume'ы (Postgres/Redis) добавьте `-v`.

> ⚠️ Без API-ключей LLM сервис вернёт шаблонные описания — это нормально для демо.

---

## 🛠 Локальная разработка (без Docker)
### Backend (gRPC + FastAPI)
```bash
poetry --version  # нужен Poetry ≥ 1.7

cd services/embedding-service
poetry install
poetry run python -m app.main  # старт gRPC сервиса
```
Повторите для `ranking-service`, `route-planner-service`, `poi-service`, `geocoding-service`, `llm-service`. Для API Gateway:
```bash
cd services/api-gateway
poetry install
poetry run uvicorn app.main:app --reload --port 8000
```

### PostgreSQL и Redis локально
Используйте готовые контейнеры:
```bash
docker run --name ai-tourist-pg -e POSTGRES_PASSWORD=ai_tourist -e POSTGRES_DB=ai_tourist -p 5432:5432 postgres:16-alpine
docker run --name ai-tourist-redis -p 6379:6379 redis:7-alpine
```

### Фронтенд
```bash
cd frontend
npm install
npm run dev -- --host
```

### Генерация protobuf
```bash
./scripts/generate-protos.sh
```
Скрипт обновит gRPC обвязки во всех сервисах.

---

## 📊 Работа с данными
- Основной датасет — `data/poi.json`.
- Для загрузки в локальную БД используйте `docker compose run --rm poi-loader` или скрипт напрямую:
  ```bash
  DATABASE_URL=postgresql+asyncpg://ai_tourist:ai_tourist@localhost:5432/ai_tourist \
  EMBEDDING_SERVICE_ADDR=localhost:50051 \
  poetry run python services/poi-service/scripts/load_pois.py
  ```
- Скрипт пересчитает эмбеддинги через gRPC и обновит таблицы.

---

## 🧪 Тестирование
- Юнит- и интеграционные тесты Python-сервисов: `pytest` внутри соответствующей директории (например, `poetry run pytest`).
- Основные проверки маршрутизатора: `pytest services/api-gateway/tests/test_route_heuristics.py services/api-gateway/tests/test_route_optimization.py`.
- Фронтенд: `npm run lint`, `npm run test`, `npm run build`.

---

## ❓ FAQ и советы
- **LLM без ключей** — сервис автоматически переключается на fallback-описания, приложение продолжит работать.
- **Geocoding без 2GIS** — запросы вернут «не удалось геокодировать», маршрут всё равно построится по заданным координатам.
- **Проблемы со сборкой Docker** — убедитесь, что включён BuildKit (`DOCKER_BUILDKIT=1`) и достаточно памяти (не менее 6 ГБ свободно).
- **Генерация proto** — запускайте `./scripts/generate-protos.sh` после правок `.proto` файлов.
- **Windows / WSL** — для Minikube используйте `make port-forward`, для Docker Compose сервисы доступны на `localhost`.

---

Счастливых прогулок по Нижнему Новгороду! 🏞
