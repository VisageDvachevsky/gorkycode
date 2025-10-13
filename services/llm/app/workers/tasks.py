import json
import logging
from typing import Dict, Any
from openai import OpenAI
from anthropic import Anthropic

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def generate_route_explanation_task(
    self,
    pois: list[Dict[str, Any]],
    interests: str,
    social_mode: str,
    intensity: str,
    provider: str,
    model: str
) -> Dict[str, Any]:
    try:
        if provider == "anthropic":
            import os
            client = Anthropic(api_key=os.getenv('ANTHROPIC_API_KEY'))
            
            prompt = _build_prompt(pois, interests, social_mode, intensity)
            
            response = client.messages.create(
                model=model,
                max_tokens=4000,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}]
            )
            content = response.content[0].text
        
        elif provider == "openai":
            import os
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            prompt = _build_prompt(pois, interests, social_mode, intensity)
            
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=4000
            )
            content = response.choices[0].message.content
        
        else:
            raise ValueError(f"Unknown provider: {provider}")
        
        result = _parse_response(content)
        
        logger.info(f"✓ Generated explanations for {len(pois)} POIs")
        return result
    
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise self.retry(exc=e, countdown=5)


def _build_prompt(pois, interests, social_mode, intensity) -> str:
    pois_text = "\n\n".join([
        f"{i+1}. {poi['name']} (ID: {poi['id']})\n"
        f"   Категория: {poi['category']}\n"
        f"   Описание: {poi['description']}\n"
        f"   Теги: {', '.join(poi['tags'])}\n"
        f"   Рейтинг: {poi['rating']}/5.0"
        for i, poi in enumerate(pois)
    ])
    
    return f"""Создай увлекательные объяснения для маршрута по Нижнему Новгороду.

ПРОФИЛЬ:
- Интересы: {interests or "разнообразные достопримечательности"}
- Формат: {social_mode}
- Темп: {intensity}

ТОЧКИ:
{pois_text}

ВАЖНО:
- Каждое "why" должно быть уникальным, с конкретными деталями
- Избегай общих фраз
- Адаптируй тон под формат прогулки

Верни ТОЛЬКО чистый JSON:
{{
    "summary": "Краткое введение в маршрут (2-3 предложения)",
    "explanations": [
        {{"poi_id": 1, "why": "Детальное объяснение", "tip": "Практичный совет"}},
        ...
    ],
    "atmospheric_description": "Поэтичное описание атмосферы",
    "notes": ["Практичная заметка 1", "Заметка 2"]
}}

НЕ используй markdown теги. Только JSON."""


def _parse_response(content: str) -> Dict[str, Any]:
    content = content.strip()
    
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    
    content = content.strip()
    
    start = content.find('{')
    end = content.rfind('}')
    if start != -1 and end != -1:
        content = content[start:end+1]
    
    return json.loads(content)