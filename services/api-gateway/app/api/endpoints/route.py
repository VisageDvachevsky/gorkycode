from datetime import datetime
import logging
from fastapi import APIRouter, HTTPException
from typing import List, Optional

from app.grpc.clients import grpc_clients
from app.proto import (
    embedding_pb2,
    ranking_pb2,
    route_pb2,
    llm_pb2,
    geocoding_pb2,
    poi_pb2,
)
from app.models.schemas import RouteRequest, RouteResponse, POIInRoute

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/plan", response_model=RouteResponse)
async def plan_route(request: RouteRequest) -> RouteResponse:
    """
    Generate personalized walking route using microservices architecture
    
    Flow:
    1. Geocoding (if address provided)
    2. Generate embedding for user query
    3. Rank POIs based on user preferences
    4. Optimize route
    5. Add coffee breaks (if requested)
    6. Generate LLM explanations
    7. Calculate route geometry
    """
    
    logger.info(f"Route planning started: {request.interests[:50] if request.interests else 'no interests'}...")
    start_time = datetime.now()
    
    # === 1. GEOCODING ===
    if request.start_address:
        logger.info(f"Geocoding address: {request.start_address}")
        
        geocode_response = await grpc_clients.geocoding.GeocodeAddress(
            geocoding_pb2.GeocodeRequest(
                address=request.start_address,
                city="Нижний Новгород"
            )
        )
        
        if not geocode_response.success:
            raise HTTPException(
                status_code=400,
                detail=f"Не удалось найти адрес: {request.start_address}"
            )
        
        start_lat, start_lon = geocode_response.lat, geocode_response.lon
        logger.info(f"Geocoded to: ({start_lat}, {start_lon})")
        
    elif request.start_lat is not None and request.start_lon is not None:
        start_lat, start_lon = request.start_lat, request.start_lon
        
        validation_response = await grpc_clients.geocoding.ValidateCoordinates(
            geocoding_pb2.CoordinateValidationRequest(
                lat=start_lat,
                lon=start_lon
            )
        )
        
        if not validation_response.valid:
            raise HTTPException(
                status_code=400,
                detail=validation_response.reason
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Укажите start_address или start_lat + start_lon"
        )
    
    # === 2. EMBEDDING GENERATION ===
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
    
    embedding_response = await grpc_clients.embedding.GenerateEmbedding(
        embedding_pb2.EmbeddingRequest(
            text=query_text,
            use_cache=True
        )
    )
    
    user_embedding = list(embedding_response.vector)
    logger.info(f"Embedding generated (cached: {embedding_response.from_cache})")
    
    # === 3. POI RANKING ===
    logger.info(f"Ranking POIs...")
    
    ranking_response = await grpc_clients.ranking.RankPOIs(
        ranking_pb2.RankingRequest(
            user_embedding=user_embedding,
            social_mode=request.social_mode or "solo",
            intensity=request.intensity or "medium",
            top_k=20,
            categories_filter=request.categories or []
        )
    )
    
    if not ranking_response.scored_pois:
        raise HTTPException(
            status_code=404,
            detail="Не найдено подходящих мест. Попробуйте другие категории."
        )
    
    logger.info(f"Found {len(ranking_response.scored_pois)} candidate POIs")
    
    # === 4. ROUTE OPTIMIZATION ===
    logger.info("Optimizing route...")
    
    poi_infos = [
        route_pb2.POIInfo(
            id=poi.poi_id,
            name=poi.name,
            lat=poi.lat,
            lon=poi.lon,
            avg_visit_minutes=poi.avg_visit_minutes,
            rating=poi.rating
        )
        for poi in ranking_response.scored_pois
    ]
    
    route_response = await grpc_clients.route.OptimizeRoute(
        route_pb2.RouteOptimizationRequest(
            start_lat=start_lat,
            start_lon=start_lon,
            pois=poi_infos,
            available_hours=request.hours
        )
    )
    
    if not route_response.optimized_route:
        raise HTTPException(
            status_code=400,
            detail=f"Невозможно создать маршрут за {request.hours} часов. Увеличьте время."
        )
    
    logger.info(f"Route optimized: {len(route_response.optimized_route)} POIs, {route_response.total_distance_km:.2f}km")
    
    # === 5. COFFEE BREAKS ===
    optimized_route = route_response.optimized_route
    
    if request.coffee_preferences and request.coffee_preferences.enabled:
        logger.info("Adding coffee breaks...")
        
        poi_list = [
            poi_pb2.POI(
                id=poi.id,
                name=poi.name,
                lat=poi.lat,
                lon=poi.lon,
                avg_visit_minutes=poi.avg_visit_minutes,
                rating=poi.rating
            )
            for poi in optimized_route
        ]
        
        coffee_response = await grpc_clients.poi.InsertCoffeeBreaks(
            poi_pb2.CoffeeBreakRequest(
                route=poi_list,
                interval_minutes=request.coffee_preferences.interval_minutes,
                preferences=poi_pb2.CoffeePreferences(
                    enabled=request.coffee_preferences.enabled,
                    interval_minutes=request.coffee_preferences.interval_minutes,
                    preferred_types=request.coffee_preferences.preferred_types or []
                )
            )
        )
        
        optimized_route = coffee_response.updated_route
        logger.info(f"Coffee breaks added, total POIs: {len(optimized_route)}")
    
    # === 6. LLM EXPLANATIONS ===
    logger.info("Generating AI explanations...")
    
    try:
        poi_contexts = [
            llm_pb2.POIContext(
                id=poi.id,
                name=poi.name,
                description=poi.description if hasattr(poi, 'description') else "",
                category=poi.category if hasattr(poi, 'category') else "",
                tags=list(poi.tags) if hasattr(poi, 'tags') else [],
                local_tip=poi.local_tip if hasattr(poi, 'local_tip') else ""
            )
            for poi in optimized_route
        ]
        
        llm_response = await grpc_clients.llm.GenerateRouteExplanation(
            llm_pb2.RouteExplanationRequest(
                route=poi_contexts,
                user_interests=request.interests or "",
                social_mode=request.social_mode or "solo",
                intensity=request.intensity or "medium"
            )
        )
        
        logger.info("✓ AI explanations generated")
        
    except Exception as e:
        logger.error(f"LLM generation failed: {str(e)}")
        llm_response = llm_pb2.RouteExplanationResponse(
            summary="Персональный маршрут создан на основе ваших предпочтений",
            explanations=[],
            notes=[],
            atmospheric_description=""
        )
    
    # === 7. ROUTE GEOMETRY ===
    logger.info("Calculating route geometry...")
    
    try:
        waypoints = [
            route_pb2.Coordinate(lat=poi.lat, lon=poi.lon)
            for poi in optimized_route
        ]
        
        geometry_response = await grpc_clients.route.CalculateRouteGeometry(
            route_pb2.RouteGeometryRequest(
                start_lat=start_lat,
                start_lon=start_lon,
                waypoints=waypoints
            )
        )
        
        route_geometry = [
            [coord.lat, coord.lon]
            for coord in geometry_response.geometry
        ]
        
    except Exception as e:
        logger.error(f"Geometry calculation failed: {str(e)}")
        route_geometry = [[start_lat, start_lon]] + [[poi.lat, poi.lon] for poi in optimized_route]
    
    # === 8. BUILD RESPONSE ===
    explanations_map = {exp.poi_id: exp for exp in llm_response.explanations}
    
    route_items = []
    current_time = datetime.now()
    
    for idx, poi in enumerate(optimized_route, 1):
        exp = explanations_map.get(poi.id, llm_pb2.POIExplanation())
        
        route_items.append(POIInRoute(
            order=idx,
            poi_id=poi.id,
            name=poi.name,
            lat=poi.lat,
            lon=poi.lon,
            why=exp.why or f"{poi.name}",
            tip=exp.tip or "",
            est_visit_minutes=poi.avg_visit_minutes,
            arrival_time=current_time,
            leave_time=current_time,
            is_coffee_break=hasattr(poi, 'category') and poi.category == "кофейня"
        ))
        
        current_time = current_time
    
    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(f"Route planning completed in {elapsed:.2f}s")
    
    return RouteResponse(
        summary=llm_response.summary,
        route=route_items,
        total_est_minutes=int(route_response.total_minutes) if hasattr(route_response, 'total_minutes') else int(request.hours * 60),
        total_distance_km=round(route_response.total_distance_km, 2),
        notes=list(llm_response.notes),
        atmospheric_description=llm_response.atmospheric_description,
        route_geometry=route_geometry
    )