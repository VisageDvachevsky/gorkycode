import logging
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
import httpx

from app.proto import poi_pb2, poi_pb2_grpc
from app.core.config import settings
from app.models.poi import POI as POIModel

logger = logging.getLogger(__name__)


class POIServicer(poi_pb2_grpc.POIServiceServicer):
    def __init__(self):
        self.engine = None
        self.session_maker = None
        self.twogis_api_key = settings.TWOGIS_API_KEY
    
    async def initialize(self):
        """Initialize database connection"""
        logger.info(f"Connecting to database...")
        
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
        """Get all POIs from database"""
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
                        rating=poi.rating or 0.0,
                        embedding=poi.embedding if request.with_embeddings else [],
                        local_tip=poi.local_tip or "",
                        photo_tip=poi.photo_tip or ""
                    )
                    for poi in pois
                ]
                
                logger.info(f"Retrieved {len(response_pois)} POIs")
                
                return poi_pb2.GetPOIsResponse(pois=response_pois)
                
        except Exception as e:
            logger.error(f"Failed to get POIs: {e}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Failed to get POIs: {str(e)}")
            return poi_pb2.GetPOIsResponse()
    
    async def FindNearbyCoffeeShops(
        self,
        request: poi_pb2.CoffeeShopRequest,
        context
    ) -> poi_pb2.CoffeeShopResponse:
        """Find nearby coffee shops using 2GIS API"""
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "q": "кофейня",
                    "point": f"{request.lon},{request.lat}",
                    "radius": request.radius_meters,
                    "limit": request.limit,
                    "key": self.twogis_api_key
                }
                
                response = await client.get(
                    "https://catalog.api.2gis.com/3.0/items",
                    params=params,
                    timeout=10.0
                )
                
                coffee_shops = []
                
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("result", {}).get("items", [])[:request.limit]:
                        point = item.get("point", {})
                        coffee_shops.append(
                            poi_pb2.CoffeeShop(
                                name=item.get("name", "Кофейня"),
                                lat=point.get("lat", 0.0),
                                lon=point.get("lon", 0.0),
                                rating=float(item.get("reviews", {}).get("rating", 0.0)),
                                avg_visit_minutes=20,
                                description=item.get("address_name", "")
                            )
                        )
                
                logger.info(f"Found {len(coffee_shops)} coffee shops")
                
                return poi_pb2.CoffeeShopResponse(coffee_shops=coffee_shops)
                
        except Exception as e:
            logger.error(f"Coffee shop search failed: {e}")
            return poi_pb2.CoffeeShopResponse(coffee_shops=[])
    
    async def InsertCoffeeBreaks(
        self,
        request: poi_pb2.CoffeeBreakRequest,
        context
    ) -> poi_pb2.CoffeeBreakResponse:
        """Insert coffee breaks into route"""
        try:
            if not request.preferences.enabled:
                return poi_pb2.CoffeeBreakResponse(updated_route=list(request.route))
            
            updated_route = []
            accumulated_minutes = 0
            interval = request.preferences.interval_minutes
            
            for poi in request.route:
                updated_route.append(poi)
                accumulated_minutes += poi.avg_visit_minutes
                
                if accumulated_minutes >= interval:
                    coffee_response = await self.FindNearbyCoffeeShops(
                        poi_pb2.CoffeeShopRequest(
                            lat=poi.lat,
                            lon=poi.lon,
                            radius_meters=500,
                            limit=1
                        ),
                        context
                    )
                    
                    if coffee_response.coffee_shops:
                        coffee = coffee_response.coffee_shops[0]
                        coffee_poi = poi_pb2.POI(
                            id=999999,
                            name=coffee.name,
                            lat=coffee.lat,
                            lon=coffee.lon,
                            category="кофейня",
                            tags=["coffee"],
                            description=coffee.description,
                            avg_visit_minutes=coffee.avg_visit_minutes,
                            rating=coffee.rating
                        )
                        updated_route.append(coffee_poi)
                        accumulated_minutes = 0
            
            logger.info(f"Inserted coffee breaks, route now has {len(updated_route)} POIs")
            
            return poi_pb2.CoffeeBreakResponse(updated_route=updated_route)
            
        except Exception as e:
            logger.error(f"Coffee break insertion failed: {e}")
            return poi_pb2.CoffeeBreakResponse(updated_route=list(request.route))