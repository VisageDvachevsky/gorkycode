# 🧭 AI-Tourist

**ИИ-помощник для прогулок по Нижнему Новгороду**

Создание персонализированных прогулочных маршрутов (3–5 реальных точек) с обоснованием выбора, таймлайном и возможностью экспорта.

---

## 🚀 Функциональность

### Входные данные

- **Интересы** — свободная форма (стрит-арт, панорамы, кофе, история…)
- **Свободное время** — в часах
- **Точка старта** — адрес или координаты
- **Social mode** — `solo` / `friends` / `family`

### Выход

- **3–5 реальных POI** с обоснованием («почему идём именно сюда»)
- **Таймлайн** — время прихода/ухода для каждой точки
- **Подсказки** — лайфхаки, лучшие ракурсы, кофейные точки
- **Экспорт** — GPX / PDF / Share Link
- **Smart Backup** — автоматическая замена закрытых или недоступных точек

---

## 🏗 Архитектура

| Компонент | Технологии |
|---|---|
| **Frontend** | React SPA + Map (Leaflet / Mapbox) |
| **Backend API** | FastAPI — orchestration pipeline |
| **Хранилище** | PostgreSQL (POI), pgvector / Pinecone, Redis cache |
| **AI Layer** | Embedding model + LLM для объяснений |
| **Routing Engine** | OSRM / GraphHopper для таймингов и дистанций |

---

## 🔧 Пайплайн генерации маршрута

1. **Embedding Service** — формирование вектора user intent
2. **Vector Search + Ranker** — подбор кандидатов и адаптивное ранжирование
3. **Route Planner (TSP-lite)** — оптимизация порядка точек
4. **LLM Generator** — финальный JSON с объяснениями и таймлайном
5. **Frontend View** — визуализация маршрута + экспорт

---

## 📦 JSON-схема ответа

```json
{
  "summary": "Краткое вступление",
  "route": [
    {
      "order": 1,
      "poi_id": 123,
      "name": "Площадь Минина",
      "lat": 56.3287,
      "lon": 44.0020,
      "why": "Почему это",
      "tip": "Совет",
      "est_visit_minutes": 20,
      "arrival_time": "2025-10-10T10:00:00+03:00",
      "leave_time": "2025-10-10T10:20:00+03:00"
    }
  ],
  "total_est_minutes": 150,
  "notes": ["Альтернатива при дожде"]
}
```

---

## 🧠 Эвристики

| Логика | Значение |
|---|---|
| **Кофе/перекус** | Каждые 90±30 минут (любителям кофе — 60–75 мин) |
| **Скорость пешехода** | 4.5 км/ч, буфер 5–10 мин |
| **Social Mode** | `solo` → тихие виды, `friends` → стритфуд/барчики |
| **Smart Backup** | Автосвап POI при закрытии/поломке точки |

---

## 💎 Killer Features

- **☕ Adaptive Coffee Breaks** — сервис сам вставляет кофейные остановки
- **🔄 Smart Backup** — авто-замена POI при недоступности
- **📸 Photo-Hints** — подсказки ракурсов для фотоэнтузиастов
- **🔗 Shareable itineraries** — ссылка + GPX/PDF экспорт
- **👥 Friend Mode Merge** — объединение интересов компании
- **💬 Explainability Panel** — почему именно эти точки
- **💰 Local Deals API** *(монетизация)* — скидки/купоны из локальных кафе

---

## 🌍 Источники POI

- **OpenStreetMap** — база точек (primary)
- **2GIS / TripAdvisor / локальные гиды** — часы работы, рейтинг
- **Кураторская ручная база** — «места, которые знают только местные»

---

## 🗓 MVP (48–72h плейбук)

### Задачи

- ✅ Импорт ~200–500 POI
- ✅ FastAPI `/plan` endpoint (embedding → search → ranking → route → LLM-json)
- ✅ React-форма + визуализация + export
- ✅ Добавить coffee heuristic, explainability, share-линк

### Демо-сценарии

- Прогулка «solo photo walk»
- «Friends food crawl»
- «Rainy day alt-route»

---

## 📊 Метрики

| Метрика | Описание |
|---|---|
| **Conversion** | Запрос → экспорт |
| **Retention** | Повторные маршруты |
| **Ranking Quality** | NDCG / MAP (после сбора фидбека) |
| **Latency** | `/plan` < 2s (без LLM), общая < 5s |

---

## 🔐 Privacy & Security

- Геолокация не сохраняется без opt-in
- Урезаем PII в промптах
- Защита ключей / rate-limiting

---

## 📌 Промпты

### Embedding prompt pattern

```
"{social} {hours}h walk, {raw_interests}, start {lat},{lon}"
```

### System prompt (LLM → JSON генерация)

```
"You are an AI guide for Nizhny Novgorod... Produce only valid JSON following the schema. Do not hallucinate new POI..."
```

*Фулл-промпты — в `/prompts`*