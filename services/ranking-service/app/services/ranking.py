import logging
import math
from collections import defaultdict
from datetime import time as dt_time
from typing import Dict, List, Optional, Tuple

import grpc
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models.poi import POI
from app.proto import ranking_pb2, ranking_pb2_grpc

logger = logging.getLogger(__name__)


class RankingServicer(ranking_pb2_grpc.RankingServiceServicer):
    SOCIAL_COMPATIBILITY: Dict[str, Tuple[str, ...]] = {
        "solo": ("friends",),
        "friends": ("solo", "couple"),
        "couple": ("friends", "family"),
        "family": ("friends",),
        "any": ("solo", "friends", "couple", "family"),
    }

    INTENSITY_ALIGNMENT: Dict[str, Dict[str, float]] = {
        "relaxed": {"relaxed": 1.0, "medium": 0.85, "intense": 0.6, "low": 1.0, "high": 0.6},
        "medium": {"relaxed": 0.9, "medium": 1.0, "intense": 0.85, "low": 0.9, "high": 0.85},
        "intense": {"relaxed": 0.65, "medium": 0.9, "intense": 1.0, "low": 0.65, "high": 1.0},
        "low": {"relaxed": 1.0, "medium": 0.85, "intense": 0.55, "low": 1.0, "high": 0.55},
        "high": {"relaxed": 0.6, "medium": 0.85, "intense": 1.0, "low": 0.6, "high": 1.0},
    }

    TYPICAL_OPENING_HOURS: Dict[str, Tuple[dt_time, dt_time]] = {
        "museum": (dt_time(10, 0), dt_time(19, 0)),
        "monument": (dt_time(0, 0), dt_time(23, 59)),
        "memorial": (dt_time(0, 0), dt_time(23, 59)),
        "park": (dt_time(0, 0), dt_time(23, 59)),
        "viewpoint": (dt_time(9, 0), dt_time(22, 0)),
        "art_object": (dt_time(9, 0), dt_time(22, 0)),
        "religious_site": (dt_time(8, 0), dt_time(20, 0)),
        "cafe": (dt_time(8, 0), dt_time(23, 0)),
        "bar": (dt_time(12, 0), dt_time(2, 0)),
        "default": (dt_time(9, 0), dt_time(21, 0)),
    }
    
    def __init__(self):
        self.engine = None
        self.session_maker = None
    
    async def initialize(self):
        logger.info("Connecting to database: %s", settings.DATABASE_URL)
        
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
                if user_embedding.size == 0:
                    logger.warning("Empty user embedding received")
                    return ranking_pb2.RankingResponse(scored_pois=[])

                category_stats, max_count, global_mean, global_std = self._compute_category_stats(pois)
                start_minutes: Optional[int] = None
                if request.HasField("start_time_minutes"):
                    start_minutes = request.start_time_minutes

                scored_pois = []

                for poi in pois:
                    if not poi.embedding:
                        continue

                    poi_embedding = np.array(poi.embedding)
                    base_similarity = self._cosine_similarity(user_embedding, poi_embedding)
                    semantic_score = self._normalize_similarity(base_similarity)

                    quality_score = self._quality_score(poi.rating, global_mean, global_std)
                    popularity_score = self._popularity_score(category_stats, poi.category, max_count)
                    context_score = self._context_alignment(
                        poi.social_mode or "any",
                        poi.intensity_level or "medium",
                        request.social_mode or "solo",
                        request.intensity or "medium",
                        poi.tags or [],
                    )
                    schedule_factor = self._schedule_factor(poi, start_minutes)

                    weighted_score = (
                        0.55 * semantic_score
                        + 0.2 * quality_score
                        + 0.15 * popularity_score
                        + 0.1 * context_score
                    ) * schedule_factor

                    scored_pois.append((poi, weighted_score))

                scored_pois.sort(key=lambda item: item[1], reverse=True)
                limited = scored_pois[: request.top_k or 20]

                response_pois = []
                for poi, score in limited:
                    response_pois.append(
                        ranking_pb2.ScoredPOI(
                            poi_id=poi.id,
                            name=poi.name,
                            lat=poi.lat,
                            lon=poi.lon,
                            category=poi.category,
                            tags=list(poi.tags or []),
                            description=poi.description or "",
                            avg_visit_minutes=poi.avg_visit_minutes,
                            rating=poi.rating or 0.0,
                            score=float(score),
                            embedding=list(poi.embedding or []),
                            social_mode=poi.social_mode or "any",
                            intensity_level=poi.intensity_level or "medium",
                            open_time=self._format_time(poi.open_time),
                            close_time=self._format_time(poi.close_time),
                        )
                    )

                logger.info("Ranked %s POIs", len(response_pois))

                return ranking_pb2.RankingResponse(scored_pois=response_pois)
                
        except Exception as exc:
            logger.error("Ranking failed: %s", exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Ranking failed: {exc}")
            return ranking_pb2.RankingResponse()

    def _cosine_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(vec1, vec2) / (norm1 * norm2))

    def _normalize_similarity(self, value: float) -> float:
        bounded = max(-1.0, min(1.0, value))
        return (bounded + 1.0) / 2.0

    def _compute_category_stats(
        self, pois: List[POI]
    ) -> Tuple[Dict[str, Dict[str, float]], int, float, float]:
        stats: Dict[str, Dict[str, float]] = defaultdict(lambda: {"count": 0, "rating_sum": 0.0})
        ratings: List[float] = []

        for poi in pois:
            category = poi.category or "unknown"
            stats[category]["count"] += 1
            rating = float(poi.rating or 0.0)
            if rating > 0:
                stats[category]["rating_sum"] += rating
                ratings.append(rating)

        max_count = max((data["count"] for data in stats.values()), default=1)

        for category, data in stats.items():
            if data["count"]:
                data["avg_rating"] = data["rating_sum"] / data["count"]
            else:
                data["avg_rating"] = 0.0

        global_mean = float(np.mean(ratings)) if ratings else 4.0
        global_std = float(np.std(ratings)) if ratings else 0.6
        if global_std == 0:
            global_std = 0.6

        return stats, max_count, global_mean, global_std

    def _quality_score(self, rating: Optional[float], mean: float, std: float) -> float:
        if not rating or rating <= 0:
            return 0.45
        normalized = (rating - mean) / max(std, 0.1)
        logistic = 1.0 / (1.0 + math.exp(-normalized))
        direct = rating / 5.0
        return max(0.3, min(1.0, 0.6 * direct + 0.4 * logistic))

    def _popularity_score(
        self, stats: Dict[str, Dict[str, float]], category: str, max_count: int
    ) -> float:
        data = stats.get(category)
        if not data:
            data = stats.get("default")
        if not data:
            return 0.6
        frequency = data["count"] / max(1, max_count)
        rating_bias = (data.get("avg_rating", 0.0) or 0.0) / 5.0
        return max(0.3, min(1.0, 0.5 * frequency + 0.5 * rating_bias))

    def _context_alignment(
        self,
        poi_social: str,
        poi_intensity: str,
        request_social: str,
        request_intensity: str,
        tags: List[str],
    ) -> float:
        social_score = self._social_alignment(poi_social.lower(), request_social.lower())
        intensity_score = self._intensity_alignment(poi_intensity.lower(), request_intensity.lower())

        adventure_tags = {"панорама", "вид", "подъём", "ночь", "бар", "квест"}
        chill_tags = {"кафе", "кондитер", "спокой", "релакс", "семья"}

        tag_bonus = 0.0
        normalized_tags = {tag.lower() for tag in tags}

        if request_intensity.lower() in {"intense", "high"} and normalized_tags & adventure_tags:
            tag_bonus += 0.05
        if request_intensity.lower() in {"relaxed", "low"} and normalized_tags & chill_tags:
            tag_bonus += 0.05

        combined = 0.55 * social_score + 0.45 * intensity_score + tag_bonus
        return max(0.0, min(1.0, combined))

    def _social_alignment(self, poi_mode: str, request_mode: str) -> float:
        poi_mode = poi_mode or "any"
        request_mode = request_mode or "solo"
        if poi_mode == "any":
            return 0.8
        if poi_mode == request_mode:
            return 1.0
        compatible = self.SOCIAL_COMPATIBILITY.get(poi_mode, ())
        if request_mode in compatible:
            return 0.88
        inverse = self.SOCIAL_COMPATIBILITY.get(request_mode, ())
        if poi_mode in inverse:
            return 0.85
        return 0.65

    def _intensity_alignment(self, poi_intensity: str, request_intensity: str) -> float:
        poi_intensity = poi_intensity or "medium"
        request_intensity = request_intensity or "medium"
        alignment_map = self.INTENSITY_ALIGNMENT.get(poi_intensity, {})
        return alignment_map.get(request_intensity, 0.75)

    def _schedule_factor(self, poi: POI, start_minutes: Optional[int]) -> float:
        if start_minutes is None:
            return 1.0

        open_minutes, close_minutes = self._schedule_window_minutes(poi)

        # Normalize start minutes into the same window domain
        effective_start = start_minutes
        if close_minutes > 24 * 60 and start_minutes <= close_minutes - 24 * 60:
            effective_start += 24 * 60

        if effective_start < open_minutes:
            diff = open_minutes - effective_start
            if diff <= 15:
                score = 1.05
            elif diff <= 60:
                score = 0.92
            elif diff <= 120:
                score = 0.8
            else:
                score = 0.65
            return max(0.55, min(1.15, score))

        if effective_start > close_minutes:
            diff = effective_start - close_minutes
            if diff <= 30:
                score = 0.9
            elif diff <= 90:
                score = 0.75
            else:
                score = 0.55
            return max(0.55, min(1.15, score))

        return 1.05

    def _schedule_window_minutes(self, poi: POI) -> Tuple[int, int]:
        open_time = poi.open_time
        close_time = poi.close_time

        if open_time is None or close_time is None:
            typical = self.TYPICAL_OPENING_HOURS.get(
                (poi.category or "default"),
                self.TYPICAL_OPENING_HOURS["default"],
            )
            if open_time is None:
                open_time = typical[0]
            if close_time is None:
                close_time = typical[1]

        open_minutes = open_time.hour * 60 + open_time.minute
        close_minutes = close_time.hour * 60 + close_time.minute

        if close_minutes <= open_minutes:
            close_minutes += 24 * 60

        return open_minutes, close_minutes

    def _format_time(self, value: Optional[dt_time]) -> str:
        if not value:
            return ""
        return value.strftime("%H:%M")
