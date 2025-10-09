# \# AI-Tourist — мини-сервис «AI-помощник туриста» для Нижнего Новгорода

# 

# \*\*Цель:\*\* генерировать персональные прогулки (3–5 реальных точек) под интересы пользователя с объяснениями «почему идём туда», таймлайном и экспортом маршрута.

# 

# ---

# 

# \## Что делает сервис

# \- Принимает: интересы в свободной форме, доступное время (в часах), стартовую точку (координаты/адрес), social mode (solo/friends/family).

# \- Возвращает: маршруты 3–5 мест с объяснениями, полезными подсказками и точным таймлайном (arrival/leave).

# \- Поддерживает: экспорт GPX/PDF/Share link, кофейные паузы, smart backup (замена закрытых мест).

# 

# ---

# 

# \## Архитектура (кратко)

# \- \*\*Frontend:\*\* React SPA (Leaflet / Mapbox).

# \- \*\*API:\*\* FastAPI — orchestration (input → embedding → vector search → ranking → route → LLM).

# \- \*\*Storage:\*\* PostgreSQL (POI), Vector store (pgvector / Pinecone), Redis cache.

# \- \*\*AI:\*\* Embedding model + LLM (генерация объяснений).  

# \- \*\*Routing:\*\* OSRM / GraphHopper для расчёта travel time.

# 

# ---

# 

# \## Основные компоненты сервиса

# 1\. \*\*Embedding Service\*\* — создание векторного представления user intent.  

# 2\. \*\*Vector Search + Ranker\*\* — поиск кандидатов + rule-based/learnable ранжирование.  

# 3\. \*\*Route Planner\*\* — выбор 3–5 мест и порядок (TSP-approx).  

# 4\. \*\*LLM Generator\*\* — формирование финального JSON с объяснениями.  

# 5\. \*\*Frontend\*\* — сбор входа и визуализация маршрута.

# 

# ---

# 

# \## JSON схема ответа

# ```json

# {

# &nbsp; "summary": "Краткое вступление",

# &nbsp; "route": \[

# &nbsp;   {

# &nbsp;     "order": 1,

# &nbsp;     "poi\_id": 123,

# &nbsp;     "name": "Площадь Минина",

# &nbsp;     "lat": 56.3287,

# &nbsp;     "lon": 44.0020,

# &nbsp;     "why": "Почему это",

# &nbsp;     "tip": "Совет",

# &nbsp;     "est\_visit\_minutes": 20,

# &nbsp;     "arrival\_time": "2025-10-10T10:00:00+03:00",

# &nbsp;     "leave\_time": "2025-10-10T10:20:00+03:00"

# &nbsp;   }

# &nbsp; ],

# &nbsp; "total\_est\_minutes": 150,

# &nbsp; "notes": \["Альтернатива при дожде"]

# }

# Ключевые эвристики

# Кофе/перекус — каждые 90±30 минут (если user любит кофе → 60–75 мин).

# 

# Пешеходная скорость: 4.5 km/h, buffer 5–10 min.

# 

# Социальные веса: solo → тихие виды; friends → бары/уличная еда.

# 

# Замена закрытых мест: automatic fallback на ближайший подходящий POI.

# 

# Killer features

# Adaptive Coffee Breaks

# 

# Smart Backup (Auto-swap закрытых мест)

# 

# Photo-Hints (лучший ракурс)

# 

# Shareable itineraries + GPX / PDF

# 

# Friend Mode (merge interests), Explainability Panel

# 

# Local deals / coupons (монетизация)

# 

# Источники данных (как собрать POI)

# OpenStreetMap (primary) — экспорт по bounding box НН.

# 

# 2GIS / TripAdvisor / локальные путеводители (hours, popularity).

# 

# Ручная курированная база для «особенных» локальных точек.

# 

# MVP roadmap (48–72h)

# Import POI (200–500).

# 

# FastAPI /plan endpoint: embedding → vector search → rule-based ranking → route → LLM JSON.

# 

# React form + map + plan view.

# 

# Add coffee heuristics, share, GPX, explainability.

# 

# Demo: 3 сценария (solo photowalk, friends food crawl, rainy day).

# 

# Мониторинг и метрики

# Конверсия: генерация → экспорт.

# 

# Retention: повторные запросы.

# 

# NDCG / MAP для ранжера (после сбора фидбека).

# 

# Latency /plan target < 2s (без LLM) / overall < 5s.

# 

# Privacy \& Security

# Не сохраняем координаты без opt-in.

# 

# Минимизируем PII в prompts.

# 

# Rate limits и защита ключей LLM.

# 

# Prompt templates (ключевые)

# Embedding phrase:

# "{social} {hours}h walk, {raw\_interests}, start {lat},{lon}" — короткая фраза для эмбеддинга.

# 

# LLM system prompt (генерация JSON):

# You are an AI guide for Nizhny Novgorod... produce only JSON matching the schema... do not invent facts...

# 

# (Полные тексты промптов в папке /prompts)

