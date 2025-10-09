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
Generate explanations for a walking route in Nizhny Novgorod.

User profile:
- Interests: {user_interests}
- Social mode: {social_mode}
- Intensity: {intensity}

Route points:
{self._format_pois_for_prompt(route)}

Return ONLY valid JSON with this structure:
{{
    "summary": "Brief engaging introduction to the route",
    "explanations": [
        {{
            "poi_id": 1,
            "why": "Personal explanation why this POI fits user interests",
            "tip": "Local tip or photo advice"
        }}
    ],
    "atmospheric_description": "Poetic description of the walk experience",
    "notes": ["Practical notes about the route"]
}}
"""
        
        if self.provider == "anthropic":
            response = await self.client.messages.create(
                model=settings.LLM_MODEL,
                max_tokens=2000,
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
            )
            content = response.choices[0].message.content
        
        return json.loads(content)
    
    def _format_pois_for_prompt(self, pois: List[POI]) -> str:
        lines = []
        for i, poi in enumerate(pois, 1):
            lines.append(
                f"{i}. {poi.name} (ID: {poi.id})\n"
                f"   Category: {poi.category}\n"
                f"   Description: {poi.description}\n"
                f"   Tags: {', '.join(poi.tags)}"
            )
        return "\n\n".join(lines)
    
    def _load_system_prompt(self) -> str:
        return """You are an expert local guide for Nizhny Novgorod, Russia.

Your task is to explain why each point in the route was selected based on user's interests.

Guidelines:
- Write in Russian
- Be personal and engaging
- Connect explanations to user's specific interests
- Provide practical local tips
- Keep explanations concise but meaningful
- Return ONLY valid JSON, no markdown formatting"""


llm_service = LLMService()