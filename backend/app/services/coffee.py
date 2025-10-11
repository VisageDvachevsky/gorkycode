import logging
from typing import List, Optional, Dict, Any, Tuple

from app.core.config import settings
from app.services.twogis_client import twogis_client
from app.models.poi import POI

logger = logging.getLogger(__name__)


class CoffeeService:
    """Service for finding cafes using 2GIS Places API"""
    
    def __init__(self):
        self.search_radius_km = 1.0  # Increased from 0.5 to 1.0 km
    
    async def find_cafes_near_location(
        self,
        lat: float,
        lon: float,
        radius_km: Optional[float] = None,
        preferences: Optional[Dict[str, Any]] = None,
        session: Optional[Any] = None
    ) -> List[Dict[str, Any]]:
        """Find cafes near a location using 2GIS Places API with DB fallback"""
        
        radius = radius_km or self.search_radius_km
        
        # Try 2GIS first
        cafes = await twogis_client.search_cafes(
            location=(lat, lon),
            radius_km=radius,
            limit=20
        )
        
        # Fallback to database if 2GIS returns nothing
        if not cafes and session:
            from sqlalchemy import select
            from app.models.poi import POI
            
            logger.info(f"Falling back to database cafes")
            result = await session.execute(
                select(POI).where(POI.category == "cafe")
            )
            db_cafes = result.scalars().all()
            
            # Filter by distance
            nearby_cafes = []
            for cafe in db_cafes:
                dist = twogis_client.calculate_distance(lat, lon, cafe.lat, cafe.lon)
                if dist <= radius:
                    nearby_cafes.append({
                        "id": str(cafe.id),
                        "name": cafe.name,
                        "lat": cafe.lat,
                        "lon": cafe.lon,
                        "address": getattr(cafe, 'address', ''),
                        "rubrics": cafe.tags[:3] if cafe.tags else [],
                        "schedule": {},
                        "distance": dist
                    })
            
            cafes = sorted(nearby_cafes, key=lambda x: x.get("distance", 999))[:10]
            if cafes:
                logger.info(f"✓ Found {len(cafes)} cafes from database")
        
        if not cafes:
            logger.warning(f"No cafes found near ({lat}, {lon}) even with fallback")
            return []
        
        if preferences:
            cafes = self._filter_by_preferences(cafes, preferences)
        
        cafes = self._score_cafes(cafes, (lat, lon))
        
        return cafes[:10]
    
    def _filter_by_preferences(
        self,
        cafes: List[Dict[str, Any]],
        preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Filter cafes based on user preferences"""
        
        filtered = []
        
        for cafe in cafes:
            skip = False
            
            if preferences.get("cuisine"):
                cuisine_pref = preferences["cuisine"].lower()
                rubrics = [r.lower() for r in cafe.get("rubrics", [])]
                if not any(cuisine_pref in r for r in rubrics):
                    continue
            
            if not skip:
                filtered.append(cafe)
        
        return filtered if filtered else cafes[:5]
    
    def _score_cafes(
        self,
        cafes: List[Dict[str, Any]],
        origin: Tuple[float, float]
    ) -> List[Dict[str, Any]]:
        """Score and sort cafes by relevance"""
        
        scored_cafes = []
        
        for cafe in cafes:
            score = 1.0
            
            distance = twogis_client.calculate_distance(
                origin[0], origin[1],
                cafe["lat"], cafe["lon"]
            )
            
            distance_score = max(0, 1.0 - (distance / self.search_radius_km))
            score += distance_score * 2
            
            rubrics = cafe.get("rubrics", [])
            if any("кофейня" in r.lower() or "coffee" in r.lower() for r in rubrics):
                score += 0.5
            
            if cafe.get("schedule"):
                score += 0.2
            
            scored_cafes.append((cafe, score))
        
        scored_cafes.sort(key=lambda x: x[1], reverse=True)
        return [cafe for cafe, _ in scored_cafes]
    
    async def find_best_cafe_for_route(
        self,
        from_poi: POI,
        to_poi: POI,
        preferences: Optional[Dict[str, Any]] = None,
        session: Optional[Any] = None
    ) -> Optional[Dict[str, Any]]:
        """Find best cafe between two POIs"""
        
        mid_lat = (from_poi.lat + to_poi.lat) / 2
        mid_lon = (from_poi.lon + to_poi.lon) / 2
        
        cafes = await self.find_cafes_near_location(
            mid_lat, mid_lon,
            radius_km=self.search_radius_km,
            preferences=preferences,
            session=session
        )
        
        if not cafes:
            return None
        
        for cafe in cafes:
            dist_from = twogis_client.calculate_distance(
                from_poi.lat, from_poi.lon,
                cafe["lat"], cafe["lon"]
            )
            dist_to = twogis_client.calculate_distance(
                cafe["lat"], cafe["lon"],
                to_poi.lat, to_poi.lon
            )
            
            detour = (dist_from + dist_to) - twogis_client.calculate_distance(
                from_poi.lat, from_poi.lon,
                to_poi.lat, to_poi.lon
            )
            
            cafe["detour_km"] = detour
        
        cafes.sort(key=lambda c: c["detour_km"])
        
        best_cafe = cafes[0]
        if best_cafe["detour_km"] < 0.3:
            return best_cafe
        
        return None
    
    def convert_to_poi(self, cafe_data: Dict[str, Any]) -> POI:
        """Convert 2GIS cafe data to POI object"""
        
        return POI(
            id=hash(cafe_data["id"]) % 1000000,
            name=cafe_data["name"],
            lat=cafe_data["lat"],
            lon=cafe_data["lon"],
            category="cafe",
            tags=["кофе", "отдых"] + cafe_data.get("rubrics", [])[:3],
            description=f"Кафе в {cafe_data.get('address', 'центре города')}",
            avg_visit_minutes=30,
            social_mode="any",
            intensity_level="relaxed",
            rating=4.0,
            embedding=None
        )


coffee_service = CoffeeService()