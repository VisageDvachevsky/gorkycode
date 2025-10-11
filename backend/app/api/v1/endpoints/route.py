from datetime import datetime, timedelta
import logging
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.schemas import POIInRoute, RouteRequest, RouteResponse
from app.services.embedding import embedding_service
from app.services.llm import llm_service
from app.services.ranking import ranking_service
from app.services.route_planner import route_planner
from app.services.geocoding import geocoding_service
from app.services.routing import routing_service
from app.services.coffee import coffee_service
from app.services.twogis_client import twogis_client

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/plan", response_model=RouteResponse)
async def plan_route(
    request: RouteRequest,
    session: AsyncSession = Depends(get_session),
) -> RouteResponse:
    """Generate personalized walking route using 2GIS APIs"""
    
    logger.info(f"Route planning started: {request.interests[:50] if request.interests else 'no interests'}...")
    start_time = datetime.now()
    
    await twogis_client.connect_redis()
    
    if request.start_address:
        logger.info(f"Geocoding address: {request.start_address}")
        coords = await geocoding_service.geocode_address(request.start_address)
        if not coords:
            raise HTTPException(
                status_code=400,
                detail=f"Не удалось найти адрес: {request.start_address}. Попробуйте указать координаты."
            )
        start_lat, start_lon = coords
        logger.info(f"Geocoded to: ({start_lat}, {start_lon})")
        
    elif request.start_lat is not None and request.start_lon is not None:
        start_lat, start_lon = request.start_lat, request.start_lon
        
        if not geocoding_service.validate_coordinates(start_lat, start_lon):
            raise HTTPException(
                status_code=400,
                detail="Координаты за пределами Нижнего Новгорода"
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Укажите start_address или start_lat + start_lon"
        )
    
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
                detail="Укажите интересы или выберите категории"
            )
        query_parts.append("interesting places")

    query_text = " ".join(query_parts)
    logger.info(f"Query text: {query_text}")
    
    user_embedding, from_cache = await embedding_service.get_embedding(query_text)
    logger.info(f"Embedding generated (cached: {from_cache})")
    
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
        raise HTTPException(
            status_code=404,
            detail="Не найдено подходящих мест. Попробуйте другие категории."
        )
    
    logger.info(f"Found {len(scored_pois)} candidate POIs")
    candidate_pois = [poi for poi, _ in scored_pois]
    
    logger.info("Optimizing route...")
    optimized_route, total_distance = route_planner.optimize_route(
        start_lat=start_lat,
        start_lon=start_lon,
        pois=candidate_pois,
        available_hours=request.hours,
    )
    
    if not optimized_route:
        raise HTTPException(
            status_code=400,
            detail=f"Невозможно создать маршрут за {request.hours} часов. Увеличьте время."
        )
    
    logger.info(f"Route optimized: {len(optimized_route)} POIs, {total_distance:.2f}km")
    
    if request.coffee_preferences and request.coffee_preferences.enabled:
        logger.info("Adding smart coffee breaks using 2GIS Places API...")
        interval = request.coffee_preferences.interval_minutes
        
        optimized_route = await route_planner.insert_smart_coffee_breaks(
            route=optimized_route,
            interval_minutes=interval,
            preferences=request.coffee_preferences.dict(),
            coffee_service=coffee_service,
            session=session
        )
        
        logger.info(f"Coffee breaks added, total POIs: {len(optimized_route)}")
    
    logger.info("Generating AI explanations...")
    try:
        llm_response = await llm_service.generate_route_explanation(
            route=optimized_route,
            user_interests=request.interests,
            social_mode=request.social_mode,
            intensity=request.intensity,
        )
        logger.info("AI explanations generated")
    except json.JSONDecodeError as e:
        logger.error(f"LLM JSON parsing failed: {str(e)}")
        llm_response = {
            "summary": "Персональный маршрут создан на основе ваших предпочтений",
            "explanations": [],
            "notes": [],
            "atmospheric_description": None
        }
    except Exception as e:
        logger.error(f"LLM generation failed: {str(e)}")
        llm_response = {
            "summary": "Персональный маршрут создан на основе ваших предпочтений",
            "explanations": [],
            "notes": [],
            "atmospheric_description": None
        }
    
    explanations_map = {exp["poi_id"]: exp for exp in llm_response.get("explanations", [])}
    
    logger.info("Building route timeline...")
    current_time = datetime.now()
    route_items = []
    prev_lat, prev_lon = start_lat, start_lon
    transit_suggestions = []
    
    for order, poi in enumerate(optimized_route, 1):
        walk_time = route_planner.calculate_walk_time_minutes(
            routing_service.calculate_distance_km(prev_lat, prev_lon, poi.lat, poi.lon)
        )
        
        if request.allow_transit:
            transit = await routing_service.get_transit_suggestion(
                (prev_lat, prev_lon),
                (poi.lat, poi.lon)
            )
            if transit:
                transit_suggestions.append({
                    "from_poi": order - 1 if order > 1 else "start",
                    "to_poi": order,
                    "suggestion": transit["suggestion"],
                    "time_saved_min": transit["time_saved_min"]
                })
                logger.info(f"Transit suggestion: {transit['suggestion']}")
        
        current_time += timedelta(minutes=walk_time)
        arrival_time = current_time
        leave_time = current_time + timedelta(minutes=poi.avg_visit_minutes)
        
        explanation = explanations_map.get(poi.id, {})
        
        is_coffee_break = (
            poi.category == "cafe" and
            request.coffee_preferences and
            request.coffee_preferences.enabled
        )
        
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
                is_coffee_break=is_coffee_break,
            )
        )
        
        current_time = leave_time
        prev_lat, prev_lon = poi.lat, poi.lon
    
    total_minutes = int((current_time - datetime.now()).total_seconds() / 60)
    
    logger.info("Calculating real route geometry using 2GIS...")
    try:
        route_geometry = await routing_service.calculate_route_geometry(
            (start_lat, start_lon),
            [(poi.lat, poi.lon) for poi in optimized_route]
        )
        logger.info(f"Route geometry calculated: {len(route_geometry)} points")
    except Exception as e:
        logger.error(f"Route geometry calculation failed: {str(e)}")
        route_geometry = [[start_lat, start_lon]] + [[poi.lat, poi.lon] for poi in optimized_route]
    
    notes = llm_response.get("notes", [])
    
    if transit_suggestions:
        notes.append("💡 Рекомендации по транспорту:")
        for ts in transit_suggestions:
            notes.append(f"  • {ts['suggestion']} (экономия {ts['time_saved_min']:.0f} мин)")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"Route planning completed in {elapsed:.2f}s")
    
    return RouteResponse(
        summary=llm_response.get("summary", "Ваш персональный маршрут готов!"),
        route=route_items,
        total_est_minutes=total_minutes,
        total_distance_km=round(total_distance, 2),
        notes=notes,
        atmospheric_description=llm_response.get("atmospheric_description"),
        route_geometry=route_geometry,
    )


@router.delete("/cache/clear")
async def clear_route_cache():
    """Clear all caches"""
    logger.info("Clearing all caches...")
    
    return {
        "status": "success",
        "message": "Cache will be cleared on next Redis restart"
    }