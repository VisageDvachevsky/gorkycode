import json
from typing import Any, Dict, List
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI

from app.core.config import settings
from app.models.poi import POI


class LLMService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        
        if self.provider == "anthropic":
            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        elif self.provider == "openai":
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    async def generate_route_explanation(
        self,
        route: List[POI],
        user_interests: str,
        social_mode: str,
        intensity: str,
    ) -> Dict[str, Any]:
        system_prompt = self._load_system_prompt()
        
        user_prompt = f"""
Создай увлекательные объяснения для пешего маршрута по Нижнему Новгороду.

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
- Интересы: {user_interests or "разнообразные достопримечательности"}
- Формат прогулки: {self._translate_social_mode(social_mode)}
- Темп: {self._translate_intensity(intensity)}

ТОЧКИ МАРШРУТА:
{self._format_pois_for_prompt(route)}

ВАЖНЫЕ ТРЕБОВАНИЯ:
1. Поле "why" должно содержать 2-3 предложения, объясняющих:
   - КОНКРЕТНУЮ связь места с интересами пользователя
   - Уникальные особенности именно этого места
   - Что пользователь увидит/почувствует/узнает здесь
   
2. Избегай общих фраз типа "интересное место" или "стоит посетить"
3. Используй яркие, запоминающиеся детали
4. Адаптируй тон под формат прогулки (романтично для пары, семейно для детей, etc)
5. Если это кофе-брейк, объясни почему именно это кафе подходит

Верни ТОЛЬКО валидный JSON:
{{
    "summary": "Краткое вдохновляющее введение в маршрут (2-3 предложения)",
    "explanations": [
        {{
            "poi_id": 1,
            "why": "Детальное объяснение ПОЧЕМУ именно это место выбрано для пользователя. Укажи конкретные детали, что здесь интересного, как это связано с интересами. Минимум 2-3 предложения с конкретикой.",
            "tip": "Практичный совет местного жителя или фотосовет"
        }}
    ],
    "atmospheric_description": "Поэтическое описание атмосферы прогулки (2-3 предложения)",
    "notes": ["Практичные заметки о маршруте, погоде, времени"]
}}
"""
        
        if self.provider == "anthropic":
            response = await self.client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=3000,
                temperature=0.8,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            content = response.content[0].text
        else:
            response = await self.client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.8,
                max_tokens=3000,
            )
            content = response.choices[0].message.content
        
        return json.loads(content)
    
    def _format_pois_for_prompt(self, pois: List[POI]) -> str:
        lines = []
        for i, poi in enumerate(pois, 1):
            lines.append(
                f"{i}. {poi.name} (ID: {poi.id})\n"
                f"   Категория: {poi.category}\n"
                f"   Описание: {poi.description}\n"
                f"   Теги: {', '.join(poi.tags)}\n"
                f"   Рейтинг: {poi.rating}/5.0"
            )
            if poi.local_tip:
                lines[-1] += f"\n   Локальный совет: {poi.local_tip}"
        return "\n\n".join(lines)
    
    def _translate_social_mode(self, mode: str) -> str:
        modes = {
            "solo": "одиночная прогулка для созерцания и фотографии",
            "friends": "прогулка с друзьями, живая атмосфера",
            "family": "семейная прогулка с детьми"
        }
        return modes.get(mode, mode)
    
    def _translate_intensity(self, intensity: str) -> str:
        intensities = {
            "relaxed": "спокойный, расслабленный темп",
            "medium": "средний темп с остановками",
            "intense": "насыщенный, активный темп"
        }
        return intensities.get(intensity, intensity)
    
    def _load_system_prompt(self) -> str:
        return """Ты — опытный местный гид по Нижнему Новгороду с глубоким знанием истории, культуры и секретных мест города.

Твоя задача — создавать ПЕРСОНАЛИЗИРОВАННЫЕ, ВДОХНОВЛЯЮЩИЕ объяснения для каждой точки маршрута.

ПРАВИЛА:
1. Пиши живым, увлекательным языком на русском
2. ИЗБЕГАЙ общих фраз — используй конкретные детали и факты
3. Связывай каждое место с интересами конкретного пользователя
4. Добавляй эмоциональную составляющую — атмосферу, ощущения
5. Включай малоизвестные факты, которые удивят
6. Адаптируй тон под формат прогулки (романтика, семья, друзья)
7. Для кафе описывай атмосферу, специализацию, почему стоит зайти именно сюда

СТРУКТУРА:
- summary: Вступление, которое задает настроение всему маршруту
- why: ДЕТАЛЬНОЕ объяснение (минимум 2-3 предложения) с конкретными деталями
- tip: Практичный совет от местного жителя
- atmospheric_description: Поэтичное описание общей атмосферы прогулки

Возвращай ТОЛЬКО валидный JSON без markdown разметки."""


llm_service = LLMService()