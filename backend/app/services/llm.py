import json
import logging
from typing import Any, Dict, List
from anthropic import AsyncAnthropic
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.models.poi import POI

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        
        if self.provider == "anthropic":
            self.client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        elif self.provider == "openai":
            self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        retry=retry_if_exception_type((json.JSONDecodeError, KeyError))
    )
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

5. ДЛЯ КАФЕ (category="cafe"):
   - НЕ придумывай описание кафе — используй ТОЛЬКО данные из "Реальная информация"
   - НЕ выдумывай кухню, график работы или фишки — всё уже указано
   - Объясни ПОЧЕМУ это кафе удобно для кофе-брейка ЗДЕСЬ И СЕЙЧАС на маршруте
   - Например: "Удобно остановиться здесь, чтобы передохнуть перед следующей частью прогулки"
   - Tip для кафе должен быть практичным: про заказ, про место у окна, про специалитет

КРИТИЧНО: Верни ТОЛЬКО чистый JSON без markdown, комментариев или лишнего текста.
Формат:
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

НЕ добавляй ```json или другие markdown теги. ТОЛЬКО JSON.
"""
        
        if self.provider == "anthropic":
            response = await self.client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=3000,
                temperature=0.7,
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
                temperature=0.7,
                max_tokens=3000,
            )
            content = response.choices[0].message.content
        
        logger.debug(f"Raw LLM response length: {len(content)} chars")
        
        # Robust JSON extraction
        parsed_json = self._extract_json(content)
        
        # Validate structure
        if not isinstance(parsed_json, dict):
            raise ValueError("LLM response is not a dict")
        
        if "explanations" not in parsed_json:
            logger.warning("LLM response missing 'explanations' field")
            parsed_json["explanations"] = []
        
        return parsed_json
    
    def _extract_json(self, content: str) -> Dict[str, Any]:
        """Robust JSON extraction from LLM response"""
        import re
        
        # Method 1: Try direct parsing
        try:
            result = json.loads(content)
            logger.debug("✓ JSON parsed directly")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"Direct parse failed: {e}")
        
        # Method 2: Strip markdown code blocks
        try:
            # Remove ```json and ``` tags
            cleaned = re.sub(r'```json\s*', '', content)
            cleaned = re.sub(r'```\s*$', '', cleaned)
            cleaned = cleaned.strip()
            result = json.loads(cleaned)
            logger.debug("✓ JSON parsed after markdown removal")
            return result
        except json.JSONDecodeError as e:
            logger.debug(f"Markdown strip failed: {e}")
        
        # Method 3: Find JSON object in text
        try:
            # Look for first { to last }
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                json_str = content[start:end+1]
                result = json.loads(json_str)
                logger.debug("✓ JSON extracted from text boundaries")
                return result
        except json.JSONDecodeError as e:
            logger.debug(f"Boundary extraction failed: {e}")
        
        # Method 4: Remove comments and try again
        try:
            # Remove // comments
            cleaned = re.sub(r'//.*', '', content)
            # Remove /* */ comments
            cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
            # Remove trailing commas
            cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
            cleaned = cleaned.strip()
            
            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start != -1 and end != -1:
                json_str = cleaned[start:end+1]
                result = json.loads(json_str)
                logger.debug("✓ JSON parsed after comment removal")
                return result
        except json.JSONDecodeError as e:
            logger.debug(f"Comment removal failed: {e}")
        
        # Fallback: return minimal structure
        logger.error(f"❌ All JSON parsing methods failed")
        logger.error(f"First 500 chars: {content[:500]}")
        logger.error(f"Last 200 chars: {content[-200:]}")
        
        return {
            "summary": "Персональный маршрут создан на основе ваших предпочтений",
            "explanations": [],
            "notes": ["Совет: посещайте места в указанном порядке для оптимального маршрута"],
            "atmospheric_description": None
        }
    
    def _format_pois_for_prompt(self, pois: List[POI]) -> str:
        lines = []
        for i, poi in enumerate(pois, 1):
            is_cafe = poi.category == "cafe"
            
            poi_info = f"{i}. {poi.name} (ID: {poi.id})\n"
            poi_info += f"   Категория: {poi.category}\n"
            
            if is_cafe:
                # For cafes, show real data and ask LLM NOT to invent
                poi_info += f"   [КАФЕ - используй только реальные данные ниже, НЕ придумывай]\n"
                poi_info += f"   Реальная информация: {poi.description}\n"
                if poi.local_tip:
                    poi_info += f"   Особенности: {poi.local_tip}\n"
                poi_info += f"   ВАЖНО: Объясни ПОЧЕМУ это кафе подходит для кофе-брейка в ЭТОЙ точке маршрута\n"
            else:
                # For regular POIs, use full description
                poi_info += f"   Описание: {poi.description}\n"
                poi_info += f"   Теги: {', '.join(poi.tags)}\n"
                poi_info += f"   Рейтинг: {poi.rating}/5.0\n"
                if poi.local_tip:
                    poi_info += f"   Локальный совет: {poi.local_tip}"
            
            lines.append(poi_info)
        
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

КРИТИЧНО - ФОРМАТ JSON:
Возвращай ТОЛЬКО чистый валидный JSON без:
- markdown разметки (```json или ```)
- комментариев (// или /* */)
- лишнего текста до или после JSON
- trailing commas

Начинай ответ с { и заканчивай }. Ничего больше."""


llm_service = LLMService()