from datetime import datetime, timedelta
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.poi import POI
from app.models.schemas import POIInRoute, RouteRequest, RouteResponse
from app.services.embedding import embedding_service
from app.services.llm import llm_service
from app.services.ranking import ranking_service
from app.services.route_planner import route_planner
from app.services.export import export_service
from fastapi.responses import Response

router = APIRouter()


@router.post("/plan", response_model=RouteResponse)
async def plan_route(
    request: RouteRequest,
    session: AsyncSession = Depends(get_session),
) -> RouteResponse:
    query_text = f"{request.social_mode} {request.hours}h walk, {request.interests}"
    user_embedding, _ = await embedding_service.get_embedding(query_text)
    
    scored_pois = await ranking_service.rank_pois(
        session=session,
        user_embedding=user_embedding,
        social_mode=request.social_mode,
        intensity=request.intensity,
        top_k=15,
    )
    
    candidate_pois = [poi for poi, _ in scored_pois]
    
    optimized_route, total_distance = route_planner.optimize_route(
        start_lat=request.start_lat,
        start_lon=request.start_lon,
        pois=candidate_pois,
        available_hours=request.hours,
    )
    
    if request.coffee_preference:
        coffee_result = await session.execute(
            select(POI).where(POI.category == "cafe")
        )
        coffee_pois = list(coffee_result.scalars().all())
        
        optimized_route = route_planner.insert_coffee_breaks(
            route=optimized_route,
            coffee_interval_minutes=request.coffee_preference,
            coffee_pois=coffee_pois,
        )
    
    llm_response = await llm_service.generate_route_explanation(
        route=optimized_route,
        user_interests=request.interests,
        social_mode=request.social_mode,
        intensity=request.intensity,
    )
    
    explanations_map = {exp["poi_id"]: exp for exp in llm_response["explanations"]}
    
    current_time = datetime.now()
    route_items = []
    
    prev_lat, prev_lon = request.start_lat, request.start_lon
    
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
                why=explanation.get("why", ""),
                tip=explanation.get("tip"),
                est_visit_minutes=poi.avg_visit_minutes,
                arrival_time=arrival_time,
                leave_time=leave_time,
                is_coffee_break=(poi.category == "cafe" and request.coffee_preference is not None),
            )
        )
        
        current_time = leave_time
        prev_lat, prev_lon = poi.lat, poi.lon
    
    total_minutes = int((current_time - datetime.now()).total_seconds() / 60)
    
    return RouteResponse(
        summary=llm_response.get("summary", ""),
        route=route_items,
        total_est_minutes=total_minutes,
        total_distance_km=round(total_distance, 2),
        notes=llm_response.get("notes", []),
        atmospheric_description=llm_response.get("atmospheric_description"),
    )


@router.post("/plan/export/gpx")
async def export_route_gpx(
    request: RouteRequest,
    session: AsyncSession = Depends(get_session),
) -> Response:
    route_response = await plan_route(request, session)
    
    gpx_content = export_service.generate_gpx(
        route=route_response.route,
        route_name=f"Walk in Nizhny Novgorod - {request.interests[:30]}"
    )
    
    return Response(
        content=gpx_content,
        media_type="application/gpx+xml",
        headers={
            "Content-Disposition": f"attachment; filename=aitourist_route_{datetime.now().strftime('%Y%m%d_%H%M%S')}.gpx"
        }
    )