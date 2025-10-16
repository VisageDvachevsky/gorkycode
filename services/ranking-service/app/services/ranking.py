import logging
import numpy as np
from typing import List, Dict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.proto import ranking_pb2, ranking_pb2_grpc
from app.core.config import settings
from app.models.poi import POI

logger = logging.getLogger(__name__)


class RankingServicer(ranking_pb2_grpc.RankingServiceServicer):
    SOCIAL_MODE_WEIGHTS = {
        "solo": {"музей": 1.2, "парк": 1.1, "смотровая": 1.3},
        "couple": {"парк": 1.3, "набережная": 1.2, "кофейня": 1.1},
        "family": {"парк": 1.4, "музей": 1.2, "аттракционы": 1.3},
        "friends": {"бар": 1.3, "кофейня": 1.2, "стрит-арт": 1.1}
    }
    
    INTENSITY_WEIGHTS = {
        "low": {"парк": 1.2, "кофейня": 1.3, "скамейка": 1.4},
        "medium": {},
        "high": {"смотровая": 1.2, "лестница": 1.1, "холм": 1.2}
    }
    
    def __init__(self):
        self.engine = None
        self.session_maker = None
    
    async def initialize(self):
        """Initialize database connection"""
        logger.info(f"Connecting to database: {settings.DATABASE_URL}")
        
        self.engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True
        )
        
        self.session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        logger.info("✓ Database connected")
    
    async def RankPOIs(
        self,
        request: ranking_pb2.RankingRequest,
        context
    ) -> ranking_pb2.RankingResponse:
        """Rank POIs based on user preferences"""
        try:
            async with self.session_maker() as session:
                stmt = select(POI)
                
                if request.categories_filter:
                    stmt = stmt.where(POI.category.in_(request.categories_filter))
                
                result = await session.execute(stmt)
                pois = result.scalars().all()
                
                if not pois:
                    logger.warning("No POIs found in database")
                    return ranking_pb2.RankingResponse(scored_pois=[])
                
                user_embedding = np.array(request.user_embedding)
                scored_pois = []
                
                for poi in pois:
                    if not poi.embedding:
                        continue
                    
                    poi_embedding = np.array(poi.embedding)
                    
                    base_score = self._cosine_similarity(user_embedding, poi_embedding)
                    
                    category_boost = self._get_category_boost(
                        poi.category,
                        request.social_mode,
                        request.intensity
                    )
                    
                    rating_boost = (poi.rating / 5.0) * 0.1 if poi.rating else 0
                    
                    final_score = base_score * category_boost + rating_boost
                    
                    scored_pois.append((poi, final_score))
                
                scored_pois.sort(key=lambda x: x[1], reverse=True)
                scored_pois = scored_pois[:request.top_k]
                
                response_pois = [
                    ranking_pb2.ScoredPOI(
                        poi_id=poi.id,
                        name=poi.name,
                        lat=poi.lat,
                        lon=poi.lon,
                        category=poi.category,
                        tags=poi.tags or [],
                        description=poi.description or "",
                        avg_visit_minutes=poi.avg_visit_minutes,
                        rating=poi.rating or 0.0,
                        score=score,
                        embedding=poi.embedding or []
                    )
                    for poi, score in scored_pois
                ]
                
                logger.info(f"Ranked {len(response_pois)} POIs")
                
                return ranking_pb2.RankingResponse(scored_pois=response_pois)
                
        except Exception as e:
            logger.error(f"Ranking failed: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Ranking failed: {str(e)}")
            return ranking_pb2.RankingResponse()
    
    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors"""
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(np.dot(vec1, vec2) / (norm1 * norm2))
    
    def _get_category_boost(self, category: str, social_mode: str, intensity: str) -> float:
        """Get boost multiplier based on category and preferences"""
        boost = 1.0
        
        if social_mode in self.SOCIAL_MODE_WEIGHTS:
            boost *= self.SOCIAL_MODE_WEIGHTS[social_mode].get(category, 1.0)
        
        if intensity in self.INTENSITY_WEIGHTS:
            boost *= self.INTENSITY_WEIGHTS[intensity].get(category, 1.0)
        
        return boost