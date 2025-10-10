from typing import List, Tuple, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.poi import POI
from app.services.embedding import embedding_service


class RankingService:
    SOCIAL_MODE_WEIGHTS = {
        "solo": {
            "viewpoint": 1.2, "museum": 1.1, "park": 1.15, "cafe": 0.9, 
            "monument": 1.1, "memorial": 1.1, "religious_site": 1.15,
            "decorative_art": 1.1, "mosaic": 1.1, "art_object": 1.1,
            "architecture": 1.15, "sculpture": 1.1
        },
        "friends": {
            "bar": 1.3, "streetfood": 1.2, "park": 1.1, "museum": 0.9, 
            "monument": 1.0, "memorial": 1.0, "cafe": 1.1,
            "decorative_art": 1.0, "art_object": 1.0
        },
        "family": {
            "park": 1.3, "museum": 1.2, "cafe": 1.1, "viewpoint": 1.0, 
            "monument": 1.1, "memorial": 1.05, "religious_site": 1.1,
            "decorative_art": 1.15
        },
    }
    
    INTENSITY_WEIGHTS = {
        "relaxed": {
            "park": 1.2, "cafe": 1.2, "viewpoint": 1.1, "monument": 1.15,
            "memorial": 1.15, "religious_site": 1.2, "decorative_art": 1.1,
            "mosaic": 1.1
        },
        "medium": {},
        "intense": {
            "museum": 1.2, "streetart": 1.3, "architecture": 1.2,
            "art_object": 1.2, "sculpture": 1.1
        },
    }
    
    async def rank_pois(
        self,
        session: AsyncSession,
        user_embedding: List[float],
        social_mode: str,
        intensity: str,
        top_k: int = 20,
        categories_filter: Optional[List[str]] = None,
    ) -> List[Tuple[POI, float]]:
        query = select(POI)
        
        if categories_filter:
            query = query.where(POI.category.in_(categories_filter))
        
        result = await session.execute(query)
        all_pois = result.scalars().all()
        
        scored_pois: List[Tuple[POI, float]] = []
        
        for poi in all_pois:
            if not poi.embedding:
                continue
            
            base_score = embedding_service.cosine_similarity(user_embedding, poi.embedding)
            
            category_boost = self._get_category_boost(poi.category, social_mode, intensity)
            rating_boost = (poi.rating / 5.0) * 0.1
            
            final_score = base_score * category_boost + rating_boost
            
            scored_pois.append((poi, final_score))
        
        scored_pois.sort(key=lambda x: x[1], reverse=True)
        return scored_pois[:top_k]
    
    def _get_category_boost(self, category: str, social_mode: str, intensity: str) -> float:
        boost = 1.0
        
        if social_mode in self.SOCIAL_MODE_WEIGHTS:
            boost *= self.SOCIAL_MODE_WEIGHTS[social_mode].get(category, 1.0)
        
        if intensity in self.INTENSITY_WEIGHTS:
            boost *= self.INTENSITY_WEIGHTS[intensity].get(category, 1.0)
        
        return boost


ranking_service = RankingService()