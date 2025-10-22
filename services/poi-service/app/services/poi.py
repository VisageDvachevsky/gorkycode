import logging
from typing import List, Optional

from datetime import time as dt_time

import grpc
import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.proto import poi_pb2, poi_pb2_grpc
from app.core.config import settings
from app.models.poi import POI as POIModel

EARTH_RADIUS_KM = 6371

logger = logging.getLogger(__name__)


class POIServicer(poi_pb2_grpc.POIServiceServicer):
    def __init__(self):
        self.engine = None
        self.session_maker = None
        self.twogis_api_key = settings.TWOGIS_API_KEY
    
    async def initialize(self):
        logger.info("Connecting to database...")
        
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
    
    async def GetAllPOIs(
        self,
        request: poi_pb2.GetPOIsRequest,
        context
    ) -> poi_pb2.GetPOIsResponse:
        try:
            async with self.session_maker() as session:
                stmt = select(POIModel)
                
                if request.categories:
                    stmt = stmt.where(POIModel.category.in_(request.categories))
                
                result = await session.execute(stmt)
                pois = result.scalars().all()
                
                response_pois = [
                    poi_pb2.POI(
                        id=poi.id,
                        name=poi.name,
                        lat=poi.lat,
                        lon=poi.lon,
                        category=poi.category,
                        tags=poi.tags or [],
                        description=poi.description or "",
                        avg_visit_minutes=poi.avg_visit_minutes,
                        rating=poi.rating,
                        embedding=poi.embedding or [] if request.with_embeddings else [],
                        local_tip=poi.local_tip or "",
                        photo_tip=poi.photo_tip or "",
                        address=poi.address or "",
                        social_mode=poi.social_mode or "any",
                        intensity_level=poi.intensity_level or "medium",
                        open_time=self._format_time(poi.open_time),
                        close_time=self._format_time(poi.close_time),
                    )
                    for poi in pois
                ]
                
                logger.info("✓ Retrieved %s POIs", len(response_pois))
                return poi_pb2.GetPOIsResponse(pois=response_pois)
                
        except Exception as exc:
            logger.error("Error fetching POIs: %s", exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {exc}")
            return poi_pb2.GetPOIsResponse()
    
    async def GetCategories(
        self,
        request: poi_pb2.GetCategoriesRequest,
        context
    ) -> poi_pb2.GetCategoriesResponse:
        try:
            async with self.session_maker() as session:
                stmt = select(
                    POIModel.category,
                    func.count(POIModel.id).label('count')
                ).group_by(POIModel.category).order_by(func.count(POIModel.id).desc())
                
                result = await session.execute(stmt)
                rows = result.all()
                
                categories = [
                    poi_pb2.Category(
                        value=row.category,
                        label=row.category.replace('_', ' ').title(),
                        count=row.count
                    )
                    for row in rows
                ]
                
                logger.info("✓ Retrieved %s categories", len(categories))
                return poi_pb2.GetCategoriesResponse(categories=categories)
                
        except Exception as exc:
            logger.error("Error fetching categories: %s", exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Database error: {exc}")
            return poi_pb2.GetCategoriesResponse()
    
    async def FindCafesNearLocation(
        self,
        request: poi_pb2.CafeSearchRequest,
        context
    ) -> poi_pb2.CafeSearchResponse:
        try:
            if self.twogis_api_key:
                cafes = await self._search_2gis_cafes(
                    lat=request.lat,
                    lon=request.lon,
                    radius_km=request.radius_km
                )
                
                if cafes:
                    return poi_pb2.CafeSearchResponse(cafes=cafes)
            
            async with self.session_maker() as session:
                stmt = select(POIModel).where(POIModel.category == "cafe")
                result = await session.execute(stmt)
                db_cafes = result.scalars().all()
                
                nearby_cafes = []
                for cafe in db_cafes:
                    distance = self._calculate_distance(
                        request.lat, request.lon,
                        cafe.lat, cafe.lon
                    )
                    
                    if distance <= request.radius_km:
                        nearby_cafes.append(
                            poi_pb2.Cafe(
                                id=str(cafe.id),
                                name=cafe.name,
                                lat=cafe.lat,
                                lon=cafe.lon,
                                address=cafe.address or "",
                                rubrics=cafe.tags[:3] if cafe.tags else [],
                                distance=distance
                            )
                        )
                
                nearby_cafes.sort(key=lambda x: x.distance)
                logger.info("✓ Found %s cafes from database", len(nearby_cafes))

                return poi_pb2.CafeSearchResponse(cafes=nearby_cafes[:10])
                
        except Exception as exc:
            logger.error("Error finding cafes: %s", exc)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Cafe search error: {exc}")
        return poi_pb2.CafeSearchResponse()

    def _format_time(self, value: Optional[dt_time]) -> str:
        if not value:
            return ""
        return value.strftime("%H:%M")
    
    async def _search_2gis_cafes(
        self,
        lat: float,
        lon: float,
        radius_km: float
    ) -> List[poi_pb2.Cafe]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://catalog.api.2gis.com/3.0/items",
                    params={
                        "q": "кафе",
                        "point": f"{lon},{lat}",
                        "radius": int(radius_km * 1000),
                        "fields": "items.point,items.address,items.rubrics,items.schedule",
                        "key": self.twogis_api_key
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    cafes = []
                    for item in data.get("result", {}).get("items", []):
                        if "point" not in item:
                            continue
                        
                        point = item["point"]
                        distance = self._calculate_distance(
                            lat, lon,
                            point["lat"], point["lon"]
                        )
                        
                        cafes.append(
                            poi_pb2.Cafe(
                                id=item.get("id", ""),
                                name=item.get("name", ""),
                                lat=point["lat"],
                                lon=point["lon"],
                                address=item.get("address", {}).get("name", ""),
                                rubrics=[r.get("name", "") for r in item.get("rubrics", [])[:3]],
                                distance=distance
                            )
                        )
                    
                    logger.info("✓ Found %s cafes from 2GIS", len(cafes))
                    return sorted(cafes, key=lambda x: x.distance)[:10]
                
        except Exception as exc:
            logger.warning("2GIS API error: %s", exc)
        
        return []
    
    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        from math import radians, cos, sin, asin, sqrt
        
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
        
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        
        return c * EARTH_RADIUS_KM
