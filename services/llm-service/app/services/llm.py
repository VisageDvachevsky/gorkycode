import logging
import json
from typing import Dict, Any

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
        """Initialize LLM clients"""
        if settings.OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("✓ OpenAI client initialized")
        
        if settings.ANTHROPIC_API_KEY:
            self.anthropic_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
            logger.info("✓ Anthropic client initialized")
    
    async def GenerateRouteExplanation(
        self,
        request: llm_pb2.RouteExplanationRequest,
        context
    ) -> llm_pb2.RouteExplanationResponse:
        """Generate explanations using LLM"""
        try:
            prompt = self._build_prompt(request)
            
            if settings.LLM_PROVIDER == "anthropic" and self.anthropic_client:
                response_text = await self._call_anthropic(prompt)
            elif settings.LLM_PROVIDER == "openai" and self.openai_client:
                response_text = await self._call_openai(prompt)
            else:
                return self._fallback_response(request)
            
            parsed = self._parse_response(response_text, request)
            
            return llm_pb2.RouteExplanationResponse(
                summary=parsed.get("summary", ""),
                explanations=parsed.get("explanations", []),
                notes=parsed.get("notes", []),
                atmospheric_description=parsed.get("atmospheric_description", "")
            )
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return self._fallback_response(request)
    
    def _build_prompt(self, request: llm_pb2.RouteExplanationRequest) -> str:
        """Build LLM prompt"""
        poi_list = "\n".join([
            f"{i+1}. {poi.name} ({poi.category}): {poi.description[:100]}"
            for i, poi in enumerate(request.route)
        ])
        
        return f"""Создай персональные объяснения для туристического маршрута в Нижнем Новгороде.

Интересы пользователя: {request.user_interests}
Социальный режим: {request.social_mode}
Интенсивность: {request.intensity}

Маршрут:
{poi_list}

Верни JSON с полями:
- summary: краткое введение (2-3 предложения)
- explanations: массив объектов {{poi_id, why, tip}}
- notes: массив полезных советов
- atmospheric_description: атмосферное описание прогулки

Ответь только JSON, без markdown."""
    
    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        response = await self.openai_client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": "Ты местный гид по Нижнему Новгороду."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    
    async def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API"""
        message = await self.anthropic_client.messages.create(
            model=settings.LLM_MODEL,
            max_tokens=2000,
            temperature=0.7,
            system="Ты местный гид по Нижнему Новгороду.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    
    def _parse_response(self, response_text: str, request: llm_pb2.RouteExplanationRequest) -> Dict[str, Any]:
        """Parse LLM response"""
        try:
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            
            data = json.loads(clean_text.strip())
            
            explanations = []
            for exp in data.get("explanations", []):
                explanations.append(
                    llm_pb2.POIExplanation(
                        poi_id=exp.get("poi_id", 0),
                        why=exp.get("why", ""),
                        tip=exp.get("tip", "")
                    )
                )
            
            return {
                "summary": data.get("summary", ""),
                "explanations": explanations,
                "notes": data.get("notes", []),
                "atmospheric_description": data.get("atmospheric_description", "")
            }
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return self._fallback_dict(request)
    
    def _fallback_response(self, request: llm_pb2.RouteExplanationRequest) -> llm_pb2.RouteExplanationResponse:
        """Fallback response when LLM fails"""
        explanations = [
            llm_pb2.POIExplanation(
                poi_id=poi.id,
                why=f"{poi.name} — {poi.description[:150]}",
                tip=poi.local_tip or "Отличное место для посещения"
            )
            for poi in request.route
        ]
        
        return llm_pb2.RouteExplanationResponse(
            summary="Персональный маршрут создан на основе ваших предпочтений",
            explanations=explanations,
            notes=[],
            atmospheric_description=""
        )
    
    def _fallback_dict(self, request: llm_pb2.RouteExplanationRequest) -> Dict[str, Any]:
        """Fallback dict"""
        explanations = [
            llm_pb2.POIExplanation(
                poi_id=poi.id,
                why=f"{poi.name}",
                tip=""
            )
            for poi in request.route
        ]
        
        return {
            "summary": "Маршрут создан",
            "explanations": explanations,
            "notes": [],
            "atmospheric_description": ""
        }