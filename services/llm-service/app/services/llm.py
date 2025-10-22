import json
import logging
import re
from typing import Any, Dict, List, Optional, Sequence

from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from openai import AsyncOpenAI
from anthropic import AsyncAnthropic

from app.proto import llm_pb2, llm_pb2_grpc
from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMServicer(llm_pb2_grpc.LLMServiceServicer):
    def __init__(self):
        self.openai_client = None
        self.anthropic_client = None

    async def initialize(self):
        logger.info("Initializing LLM Service with provider: %s", settings.LLM_PROVIDER)

        if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("✓ OpenAI client initialized")
        elif settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
            self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            logger.info("✓ Anthropic client initialized")
        else:
            logger.warning("⚠ No LLM provider configured, will use fallback responses")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=5),
        retry=retry_if_exception_type((json.JSONDecodeError, KeyError, ValueError))
    )
    async def GenerateRouteExplanation(
        self,
        request: llm_pb2.RouteExplanationRequest,
        context
    ) -> llm_pb2.RouteExplanationResponse:
        try:
            system_prompt = self._load_system_prompt()
            user_prompt = self._build_detailed_prompt(request)
            expected_poi_ids = [poi.id for poi in request.route]
            response_format = None

            if settings.LLM_PROVIDER == "openai" and expected_poi_ids:
                response_format = self._build_openai_response_format(expected_poi_ids)

            if settings.LLM_PROVIDER == "anthropic" and self.anthropic_client:
                response_text = await self._call_anthropic(system_prompt, user_prompt)
            elif settings.LLM_PROVIDER == "openai" and self.openai_client:
                response_text = await self._call_openai(
                    system_prompt,
                    user_prompt,
                    response_format=response_format,
                )
            else:
                logger.warning("No LLM provider available, using fallback")
                return self._fallback_response(request)

            parsed = self._extract_json(response_text)

            if not isinstance(parsed, dict):
                raise ValueError("LLM response is not a dict")

            if "explanations" not in parsed:
                logger.error("LLM response missing 'explanations' field")
                raise ValueError("Missing explanations field")

            explanations = self._normalise_explanations(
                parsed["explanations"],
                expected_poi_ids,
            )
            expected_set = set(expected_poi_ids)
            received_poi_ids = {
                exp["poi_id"]
                for exp in explanations
                if "poi_id" in exp and isinstance(exp["poi_id"], int)
            }

            missing_ids = expected_set - received_poi_ids
            if missing_ids:
                logger.error("❌ LLM missing explanations for POI IDs: %s", missing_ids)
                raise ValueError(f"Missing explanations for POI IDs: {missing_ids}")

            generic_patterns = [
                "интересное место в категории",
                "стоит посетить",
                "рекомендую побывать",
                "хорошее место для"
            ]

            for exp in explanations:
                why_lower = exp.get("why", "").lower()
                if any(pattern in why_lower for pattern in generic_patterns):
                    poi_id = exp.get('poi_id')
                    snippet = exp.get('why', '')[:100]
                    logger.error("❌ Generic response detected for POI %s: %s", poi_id, snippet)
                    raise ValueError(f"Generic response detected for POI {poi_id}")

            logger.info("✓ LLM response validated: %s explanations, all unique", len(explanations))

            order_map = {poi.id: idx for idx, poi in enumerate(request.route)}
            explanations.sort(
                key=lambda exp: order_map.get(exp.get("poi_id", -1), len(order_map))
            )

            pb_explanations = [
                llm_pb2.POIExplanation(
                    poi_id=exp.get("poi_id", 0),
                    why=exp.get("why", ""),
                    tip=exp.get("tip", "")
                )
                for exp in explanations
            ]

            return llm_pb2.RouteExplanationResponse(
                summary=parsed.get("summary", ""),
                explanations=pb_explanations,
                notes=parsed.get("notes", []),
                atmospheric_description=parsed.get("atmospheric_description", "")
            )

        except Exception as exc:
            logger.error("LLM generation failed: %s", exc)
            return self._fallback_response(request)

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

ЗАПРЕТЫ:
- "Интересное место в категории X"
- "Стоит посетить"
- "Рекомендую побывать"
- Любые шаблонные фразы без конкретики

СТРУКТУРА:
- summary: Вступление, которое задает настроение всему маршруту
- why: ДЕТАЛЬНОЕ объяснение (минимум 2-3 предложения) с КОНКРЕТНЫМИ деталями
- tip: Практичный совет от местного жителя
- atmospheric_description: Поэтичное описание общей атмосферы прогулки

КРИТИЧНО - ФОРМАТ JSON:
Возвращай ТОЛЬКО чистый валидный JSON без:
- markdown разметки (```json или ```)
- комментариев (// или /* */)
- лишнего текста до или после JSON
- trailing commas

Начинай ответ с { и заканчивай }. Ничего больше."""

    def _build_detailed_prompt(self, request: llm_pb2.RouteExplanationRequest) -> str:
        poi_list = self._format_pois_for_prompt(list(request.route))

        return f"""
Создай увлекательные объяснения для пешего маршрута по Нижнему Новгороду.

ПРОФИЛЬ ПОЛЬЗОВАТЕЛЯ:
- Интересы: {request.user_interests or "разнообразные достопримечательности"}
- Формат прогулки: {self._translate_social_mode(request.social_mode)}
- Темп: {self._translate_intensity(request.intensity)}

ТОЧКИ МАРШРУТА:
{poi_list}

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

Формат JSON (ДЛЯ КАЖДОГО POI из списка выше):
{{
    "summary": "Краткое вдохновляющее введение в маршрут (2-3 предложения)",
    "explanations": {{
        "160": {{
            "poi_id": 160,
            "why": "КОНКРЕТНОЕ детальное объяснение с фактами и деталями. НЕ GENERIC! Минимум 2-3 предложения с РЕАЛЬНЫМИ деталями места.",
            "tip": "Практичный совет местного жителя или фотосовет"
        }}
        // ... блок для КАЖДОГО POI с ключом = ID в виде строки
    }},
    "atmospheric_description": "Поэтическое описание атмосферы прогулки (2-3 предложения)",
    "notes": ["Практичные заметки о маршруте, погоде, времени"]
}}

ВАЖНО: В объекте explanations должно быть ровно столько ключей, сколько POI в списке выше, каждый ключ — строка ID.

НЕ добавляй ```json или другие markdown теги. ТОЛЬКО JSON.
"""

    def _format_pois_for_prompt(self, pois: List[llm_pb2.POIContext]) -> str:
        lines = []
        for i, poi in enumerate(pois, 1):
            is_cafe = poi.category == "cafe"

            poi_info = f"{i}. {poi.name} (ID: {poi.id})\n"
            poi_info += f"   Категория: {poi.category}\n"

            if is_cafe:
                poi_info += f"   [КАФЕ - используй только реальные данные ниже, НЕ придумывай]\n"
                poi_info += f"   Реальная информация: {poi.description}\n"
                if poi.local_tip:
                    poi_info += f"   Особенности: {poi.local_tip}\n"
                poi_info += f"   ВАЖНО: Объясни ПОЧЕМУ это кафе подходит для кофе-брейка в ЭТОЙ точке маршрута\n"
            else:
                poi_info += f"   Описание: {poi.description}\n"
                if poi.tags:
                    poi_info += f"   Теги: {', '.join(poi.tags)}\n"
                if poi.local_tip:
                    poi_info += f"   Локальный совет: {poi.local_tip}"

            lines.append(poi_info)

        return "\n\n".join(lines)

    def _translate_social_mode(self, mode: str) -> str:
        modes = {
            "solo": "одиночная прогулка для созерцания и фотографии",
            "couple": "прогулка вдвоём, романтическая атмосфера",
            "friends": "прогулка с друзьями, живая атмосфера",
            "family": "семейная прогулка с детьми"
        }
        return modes.get(mode, mode)

    def _translate_intensity(self, intensity: str) -> str:
        intensities = {
            "low": "спокойный, расслабленный темп",
            "relaxed": "спокойный, расслабленный темп",
            "medium": "средний темп с остановками",
            "high": "насыщенный, активный темп",
            "intense": "насыщенный, активный темп"
        }
        return intensities.get(intensity, intensity)

    async def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        kwargs: Dict[str, Any] = {
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 4000,
        }

        if response_format:
            kwargs["response_format"] = response_format

        response = await self.openai_client.chat.completions.create(**kwargs)
        return response.choices[0].message.content

    async def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        message = await self.anthropic_client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=4000,
            temperature=0.7,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        return message.content[0].text

    def _extract_json(self, content: str) -> Dict[str, Any]:
        try:
            result = json.loads(content)
            logger.debug("✓ JSON parsed directly")
            return result
        except json.JSONDecodeError as exc:
            logger.debug("Direct parse failed: %s", exc)

        try:
            cleaned = re.sub(r'```json\s*', '', content)
            cleaned = re.sub(r'```\s*$', '', cleaned)
            cleaned = cleaned.strip()
            result = json.loads(cleaned)
            logger.debug("✓ JSON parsed after markdown removal")
            return result
        except json.JSONDecodeError as exc:
            logger.debug("Markdown strip failed: %s", exc)

        try:
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                json_str = content[start:end + 1]
                result = json.loads(json_str)
                logger.debug("✓ JSON extracted from text boundaries")
                return result
        except json.JSONDecodeError as exc:
            logger.debug("Boundary extraction failed: %s", exc)

        try:
            cleaned = re.sub(r'//.*', '', content)
            cleaned = re.sub(r'/\*.*?\*/', '', cleaned, flags=re.DOTALL)
            cleaned = re.sub(r',(\s*[}\]])', r'\1', cleaned)
            cleaned = cleaned.strip()

            start = cleaned.find('{')
            end = cleaned.rfind('}')
            if start != -1 and end != -1:
                json_str = cleaned[start:end + 1]
                result = json.loads(json_str)
                logger.debug("✓ JSON parsed after comment removal")
                return result
        except json.JSONDecodeError as exc:
            logger.debug("Comment removal failed: %s", exc)

        logger.error("❌ All JSON parsing methods failed")
        logger.error("First 500 chars: %s", content[:500])
        logger.error("Last 200 chars: %s", content[-200:])

        raise json.JSONDecodeError("Failed to parse LLM response", content, 0)

    def _fallback_response(self, request: llm_pb2.RouteExplanationRequest) -> llm_pb2.RouteExplanationResponse:
        explanations = [
            llm_pb2.POIExplanation(
                poi_id=poi.id,
                why=f"{poi.name} — {poi.description[:150] if poi.description else 'Интересное место для посещения'}",
                tip=poi.local_tip or "Отличное место для посещения"
            )
            for poi in request.route
        ]

        return llm_pb2.RouteExplanationResponse(
            summary="Персональный маршрут создан на основе ваших предпочтений",
            explanations=explanations,
            notes=["Маршрут оптимизирован по времени и расстоянию"],
            atmospheric_description="Приятная прогулка по интересным местам Нижнего Новгорода"
        )

    def _build_openai_response_format(
        self, expected_ids: Sequence[int]
    ) -> Dict[str, Any]:
        explanation_properties = {
            str(poi_id): {
                "type": "object",
                "required": ["poi_id", "why"],
                "properties": {
                    "poi_id": {"type": "integer", "enum": [poi_id]},
                    "why": {"type": "string", "minLength": 80},
                    "tip": {"type": "string"},
                },
                "additionalProperties": False,
            }
            for poi_id in expected_ids
        }

        return {
            "type": "json_schema",
            "json_schema": {
                "name": "route_explanation_payload",
                "strict": True,
                "schema": {
                    "type": "object",
                    "required": [
                        "summary",
                        "explanations",
                        "atmospheric_description",
                    ],
                    "additionalProperties": False,
                    "properties": {
                        "summary": {"type": "string", "minLength": 40},
                        "explanations": {
                            "type": "object",
                            "properties": explanation_properties,
                            "required": [str(poi_id) for poi_id in expected_ids],
                            "additionalProperties": False,
                        },
                        "atmospheric_description": {
                            "type": "string",
                            "minLength": 40,
                        },
                        "notes": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
        }

    def _normalise_explanations(
        self,
        payload: Any,
        expected_ids: Sequence[int],
    ) -> List[Dict[str, Any]]:
        if isinstance(payload, list):
            return [
                {
                    "poi_id": int(exp.get("poi_id")) if "poi_id" in exp else 0,
                    "why": exp.get("why", ""),
                    "tip": exp.get("tip", ""),
                }
                for exp in payload
                if isinstance(exp, dict)
            ]

        if isinstance(payload, dict):
            explanations: List[Dict[str, Any]] = []
            for poi_id in expected_ids:
                key = str(poi_id)
                data = payload.get(key)
                if not isinstance(data, dict):
                    continue
                why = data.get("why", "")
                tip = data.get("tip", "")
                explanations.append({
                    "poi_id": poi_id,
                    "why": why,
                    "tip": tip,
                })
            return explanations

        raise ValueError("Unexpected explanations format from LLM")
