from typing import List, Tuple, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.poi import POI
from app.services.embedding import embedding_service
from app.services.twogis_client import twogis_client


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

    BASE_SPREAD_KM = {
        "relaxed": 0.4,
        "medium": 0.3,
        "intense": 0.24,
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
        return self._select_diverse_pois(scored_pois, intensity, top_k)
    
    def _get_category_boost(self, category: str, social_mode: str, intensity: str) -> float:
        boost = 1.0
        
        if social_mode in self.SOCIAL_MODE_WEIGHTS:
            boost *= self.SOCIAL_MODE_WEIGHTS[social_mode].get(category, 1.0)
        
        if intensity in self.INTENSITY_WEIGHTS:
            boost *= self.INTENSITY_WEIGHTS[intensity].get(category, 1.0)

        return boost

    def _select_diverse_pois(
        self,
        scored_pois: List[Tuple[POI, float]],
        intensity: str,
        top_k: int,
    ) -> List[Tuple[POI, float]]:
        if not scored_pois:
            return []

        base_threshold = self.BASE_SPREAD_KM.get(intensity, self.BASE_SPREAD_KM["medium"])
        thresholds = [
            base_threshold,
            max(base_threshold * 0.75, 0.2),
            max(base_threshold * 0.5, 0.14),
            0.1,
        ]

        deduped_thresholds: List[float] = []
        for value in thresholds:
            value = round(value, 6)
            if value <= 0:
                continue
            if not deduped_thresholds or value < deduped_thresholds[-1]:
                deduped_thresholds.append(value)

        thresholds = deduped_thresholds

        selected: List[Tuple[POI, float]] = []
        selected_ids = set()

        for threshold in thresholds:
            if len(selected) >= top_k:
                break

            for poi, score in scored_pois:
                if poi.id in selected_ids:
                    continue

                if self._is_far_enough(poi, selected, threshold):
                    selected.append((poi, score))
                    selected_ids.add(poi.id)

                    if len(selected) >= top_k:
                        break

        return selected

    def _is_far_enough(
        self,
        poi: POI,
        selected: List[Tuple[POI, float]],
        min_distance_km: float,
    ) -> bool:
        if min_distance_km <= 0.0 or not selected:
            return True

        for existing, _ in selected:
            distance = twogis_client.calculate_distance(
                poi.lat,
                poi.lon,
                existing.lat,
                existing.lon,
            )
            if distance < min_distance_km:
                return False

        return True


ranking_service = RankingService()