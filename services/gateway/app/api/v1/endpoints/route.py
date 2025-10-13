from datetime import datetime, timedelta
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.schemas import RouteRequest, RouteResponse, POIInRoute
from app.grpc_clients import ml_client, llm_client, routing_client, geocoding_client
from app.models.poi import POI
from sqlalchemy import select

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/plan", response_model=RouteResponse)
async def plan_route(
    request: RouteRequest,
    session: AsyncSession = Depends(get_session)
) -> RouteResponse:
    logger.info(f"Planning route: {request.interests[:50] if request.interests else 'no interests'}")
    start_time = datetime.now()
    
    # === 1. GEOCODING ===
    if request.start_address:
        logger.info(f"Geocoding: {request.start_address}")
        coords = await geocoding_client.geocode(request.start_address)
        if not coords:
            raise HTTPException(400, f"Address not found: {request.start_address}")
        start_lat, start_lon = coords
        logger.info(f"✓ Geocoded: {start_lat}, {start_lon}")
    elif request.start_lat and request.start_lon:
        start_lat, start_lon = request.start_lat, request.start_lon
    else:
        raise HTTPException(400, "Provide start_address or coordinates")
    
    # === 2. EMBEDDING ===
    query_parts = []
    if request.social_mode:
        query_parts.append(request.social_mode)
    query_parts.append(f"{request.hours}h walk")
    if request.interests:
        query_parts.append(request.interests)
    if request.categories:
        query_parts.extend(request.categories)
    
    query_text = " ".join(query_parts)
    logger.info(f"Generating embedding for: {query_text[:100]}")
    
    user_embedding, from_cache = await ml_client.generate_embedding(query_text, use_cache=True)
    logger.info(f"✓ Embedding generated (cached: {from_cache})")
    
    # === 3. RANKING ===
    query = select(POI)
    if request.categories:
        query = query.where(POI.category.in_(request.categories))
    
    result = await session.execute(query)
    all_pois = result.scalars().all()
    
    scored_pois = []
    for poi in all_pois:
        if not poi.embedding:
            continue
        
        similarity = await ml_client.cosine_similarity(user_embedding, poi.embedding)
        scored_pois.append((poi, similarity))
    
    scored_pois.sort(key=lambda x: x[1], reverse=True)
    top_pois = [poi for poi, _ in scored_pois[:20]]
    
    logger.info(f"✓ Ranked {len(scored_pois)} POIs, selected top {len(top_pois)}")
    
    # === 4. ROUTE OPTIMIZATION ===
    pois_data = [
        {
            "id": poi.id,
            "lat": poi.lat,
            "lon": poi.lon,
            "avg_visit_minutes": poi.avg_visit_minutes
        }
        for poi in top_pois
    ]
    
    poi_order, total_distance, total_time = await routing_client.optimize_route(
        start_lat, start_lon, pois_data, request.hours
    )
    
    optimized_pois = [next(p for p in top_pois if p.id == poi_id) for poi_id in poi_order]
    logger.info(f"✓ Route optimized: {len(optimized_pois)} POIs, {total_distance:.2f}km")
    
    # === 5. LLM EXPLANATIONS ===
    llm_pois = [
        {
            "id": poi.id,
            "name": poi.name,
            "category": poi.category,
            "tags": poi.tags,
            "description": poi.description,
            "local_tip": poi.local_tip,
            "rating": poi.rating
        }
        for poi in optimized_pois
    ]
    
    try:
        llm_result = await llm_client.generate_explanation(
            llm_pois,
            request.interests or "",
            request.social_mode,
            request.intensity
        )
        logger.info("✓ LLM explanations generated")
    except Exception as e:
        logger.error(f"LLM failed: {e}, using fallback")
        llm_result = {
            "summary": "Your personalized route is ready",
            "explanations": [
                {"poi_id": poi.id, "why": poi.description[:200], "tip": poi.local_tip}
                for poi in optimized_pois
            ],
            "notes": [],
            "atmospheric_description": None
        }
    
    # === 6. BUILD TIMELINE ===
    route_start = datetime.now()
    current_time = route_start
    route_items = []
    prev_lat, prev_lon = start_lat, start_lon
    
    for order, poi in enumerate(optimized_pois, 1):
        walk_time = int((haversine(prev_lat, prev_lon, poi.lat, poi.lon) / 4.5) * 60) + 5
        
        current_time += timedelta(minutes=walk_time)
        arrival = current_time
        leave = current_time + timedelta(minutes=poi.avg_visit_minutes)
        
        explanation = next(
            (exp for exp in llm_result["explanations"] if exp["poi_id"] == poi.id),
            {"why": poi.description, "tip": poi.local_tip}
        )
        
        route_items.append(POIInRoute(
            order=order,
            poi_id=poi.id,
            name=poi.name,
            lat=poi.lat,
            lon=poi.lon,
            why=explanation["why"],
            tip=explanation.get("tip"),
            est_visit_minutes=poi.avg_visit_minutes,
            arrival_time=arrival,
            leave_time=leave,
            is_coffee_break=False
        ))
        
        current_time = leave
        prev_lat, prev_lon = poi.lat, poi.lon
    
    # === 7. ROUTE GEOMETRY ===
    waypoints = [(start_lat, start_lon)] + [(poi.lat, poi.lon) for poi in optimized_pois]
    
    try:
        geometry = await routing_client.calculate_geometry(waypoints)
        geometry_formatted = [[lat, lon] for lat, lon in geometry]
        logger.info(f"✓ Geometry calculated: {len(geometry_formatted)} points")
    except:
        geometry_formatted = [[lat, lon] for lat, lon in waypoints]
        logger.warning("Geometry calculation failed, using waypoints")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"✅ Route planning completed in {elapsed:.2f}s")
    
    return RouteResponse(
        summary=llm_result["summary"],
        route=route_items,
        total_est_minutes=total_time,
        total_distance_km=round(total_distance, 2),
        notes=llm_result.get("notes", []),
        atmospheric_description=llm_result.get("atmospheric_description"),
        route_geometry=geometry_formatted
    )


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    from math import radians, sin, cos, sqrt, atan2
    R = 6371.0
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c