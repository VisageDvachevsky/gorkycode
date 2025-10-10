from datetime import datetime, timedelta
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.poi import POI
from app.models.schemas import POIInRoute, RouteRequest, RouteResponse
from app.services.embedding import embedding_service
from app.services.llm import llm_service
from app.services.ranking import ranking_service
from app.services.route_planner import route_planner
from app.services.geocoding import geocoding_service
from app.services.routing import routing_service
from fastapi.responses import Response

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/plan", response_model=RouteResponse)
async def plan_route(
    request: RouteRequest,
    session: AsyncSession = Depends(get_session),
) -> RouteResponse:
    """
    Generate personalized walking route
    
    This endpoint:
    1. Geocodes address or validates coordinates
    2. Generates user interest embedding
    3. Ranks POIs based on preferences
    4. Optimizes route order
    5. Optionally inserts coffee breaks
    6. Generates AI explanations
    7. Calculates real walking paths
    """
    logger.info(f"Route planning started: {request.interests[:50]}...")
    start_time = datetime.now()
    
    # Step 1: Determine starting coordinates
    if request.start_address:
        logger.info(f"Geocoding address: {request.start_address}")
        coords = await geocoding_service.geocode_address(request.start_address)
        if not coords:
            logger.error(f"Geocoding failed for: {request.start_address}")
            raise HTTPException(
                status_code=400,
                detail=f"Could not find location: {request.start_address}. Try being more specific or use coordinates."
            )
        start_lat, start_lon = coords
        logger.info(f"Geocoded to: ({start_lat}, {start_lon})")
        
    elif request.start_lat is not None and request.start_lon is not None:
        start_lat, start_lon = request.start_lat, request.start_lon
        
        if not await geocoding_service.validate_coordinates(start_lat, start_lon):
            logger.warning(f"Coordinates outside Nizhny Novgorod: ({start_lat}, {start_lon})")
            raise HTTPException(
                status_code=400,
                detail="Coordinates are outside Nizhny Novgorod. Please check your location."
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Either start_address or both start_lat and start_lon must be provided"
        )
    
    # Step 2: Generate user embedding
    query_parts = []

    if request.social_mode:
        query_parts.append(request.social_mode)

    query_parts.append(f"{request.hours}h walk")

    if request.interests and request.interests.strip():
        query_parts.append(request.interests)

    if request.categories:
        query_parts.extend(request.categories)

    if not query_parts or len(query_parts) <= 2: 
        if not request.categories:
            raise HTTPException(
                status_code=400,
                detail="Please specify either interests or select at least one category"
            )
        query_parts.append("interesting places")

    query_text = " ".join(query_parts)

    logger.info(f"Query text: {query_text}")
    user_embedding, from_cache = await embedding_service.get_embedding(query_text)
    logger.info(f"Embedding generated (cached: {from_cache})")
    
    # Step 3: Rank POIs
    logger.info(f"Ranking POIs (categories: {request.categories or 'all'})...")
    scored_pois = await ranking_service.rank_pois(
        session=session,
        user_embedding=user_embedding,
        social_mode=request.social_mode,
        intensity=request.intensity,
        top_k=20,
        categories_filter=request.categories,
    )
    
    if not scored_pois:
        logger.error("No suitable POIs found")
        raise HTTPException(
            status_code=404,
            detail="No suitable places found for your criteria. Try different categories or interests."
        )
    
    logger.info(f"Found {len(scored_pois)} candidate POIs")
    candidate_pois = [poi for poi, _ in scored_pois]
    
    # Step 4: Optimize route
    logger.info("Optimizing route...")
    optimized_route, total_distance = route_planner.optimize_route(
        start_lat=start_lat,
        start_lon=start_lon,
        pois=candidate_pois,
        available_hours=request.hours,
    )
    
    if not optimized_route:
        logger.error("Could not create route within time limit")
        raise HTTPException(
            status_code=400,
            detail=f"Cannot create a route within {request.hours} hours. Try increasing the duration."
        )
    
    logger.info(f"Route optimized: {len(optimized_route)} POIs, {total_distance:.2f}km")
    
    # Step 5: Insert coffee breaks if requested
    if request.coffee_preference and optimized_route:
        logger.info(f"Adding coffee breaks (interval: {request.coffee_preference}min)...")
        
        coffee_query = select(POI).where(POI.category == "cafe")
        if request.categories and "cafe" not in request.categories:
            logger.info("Cafe category not selected, skipping coffee breaks")
        else:
            coffee_result = await session.execute(coffee_query)
            coffee_pois = list(coffee_result.scalars().all())
            
            if coffee_pois:
                original_length = len(optimized_route)
                optimized_route = route_planner.insert_coffee_breaks(
                    route=optimized_route,
                    coffee_interval_minutes=request.coffee_preference,
                    coffee_pois=coffee_pois,
                )
                added_cafes = len(optimized_route) - original_length
                logger.info(f"Added {added_cafes} coffee breaks")
            else:
                logger.warning("No cafes available for coffee breaks")
    
    # Step 6: Generate LLM explanations
    logger.info("Generating AI explanations...")
    try:
        llm_response = await llm_service.generate_route_explanation(
            route=optimized_route,
            user_interests=request.interests,
            social_mode=request.social_mode,
            intensity=request.intensity,
        )
        logger.info("AI explanations generated")
    except Exception as e:
        logger.error(f"LLM generation failed: {str(e)}")
        llm_response = {
            "summary": "Персональный маршрут создан на основе ваших предпочтений",
            "explanations": [],
            "notes": ["LLM недоступен, используются стандартные описания"],
            "atmospheric_description": None
        }
    
    explanations_map = {exp["poi_id"]: exp for exp in llm_response.get("explanations", [])}
    
    # Step 7: Build route timeline
    logger.info("Building route timeline...")
    current_time = datetime.now()
    route_items = []
    prev_lat, prev_lon = start_lat, start_lon
    
    for order, poi in enumerate(optimized_route, 1):
        walk_time = route_planner.calculate_walk_time_minutes(
            route_planner.calculate_distance_km(prev_lat, prev_lon, poi.lat, poi.lon)
        )
        
        current_time += timedelta(minutes=walk_time)
        arrival_time = current_time
        leave_time = current_time + timedelta(minutes=poi.avg_visit_minutes)
        
        explanation = explanations_map.get(poi.id, {})
        
        route_items.append(
            POIInRoute(
                order=order,
                poi_id=poi.id,
                name=poi.name,
                lat=poi.lat,
                lon=poi.lon,
                why=explanation.get("why", f"Интересное место в категории {poi.category}"),
                tip=explanation.get("tip", poi.local_tip),
                est_visit_minutes=poi.avg_visit_minutes,
                arrival_time=arrival_time,
                leave_time=leave_time,
                is_coffee_break=(poi.category == "cafe" and request.coffee_preference is not None),
            )
        )
        
        current_time = leave_time
        prev_lat, prev_lon = poi.lat, poi.lon
    
    total_minutes = int((current_time - datetime.now()).total_seconds() / 60)
    
    # Step 8: Calculate real route geometry
    logger.info("Calculating route geometry...")
    try:
        route_geometry = await routing_service.calculate_route_geometry(
            (start_lat, start_lon),
            [(poi.lat, poi.lon) for poi in optimized_route]
        )
        logger.info(f"Route geometry calculated: {len(route_geometry)} points")
    except Exception as e:
        logger.error(f"Route geometry calculation failed: {str(e)}")
        route_geometry = [[start_lat, start_lon]] + [[poi.lat, poi.lon] for poi in optimized_route]
    
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"Route planning completed in {elapsed:.2f}s")
    
    return RouteResponse(
        summary=llm_response.get("summary", "Ваш персональный маршрут готов!"),
        route=route_items,
        total_est_minutes=total_minutes,
        total_distance_km=round(total_distance, 2),
        notes=llm_response.get("notes", []),
        atmospheric_description=llm_response.get("atmospheric_description"),
        route_geometry=route_geometry,
    )


@router.delete("/cache/clear")
async def clear_route_cache():
    """Clear all route and geocoding caches"""
    logger.info("Clearing caches...")
    
    routing_cleared = await routing_service.clear_cache()
    
    logger.info(f"Cache cleared: {routing_cleared} routing entries")
    
    return {
        "status": "success",
        "routing_entries_cleared": routing_cleared,
        "message": "Cache cleared successfully"
    }