import asyncio
import json
from app.core.database import init_db, async_session_maker
from app.services.embedding import embedding_service
from app.services.ranking import ranking_service
from app.services.route_planner import route_planner
from app.services.llm import llm_service


async def generate_sample():
    print("🗺️  Generating sample route...\n")
    
    await init_db()
    await embedding_service.connect_redis()
    
    interests = "architecture history panoramic views coffee"
    hours = 3.0
    start_lat = 56.3287
    start_lon = 44.002
    social_mode = "solo"
    intensity = "medium"
    
    print(f"📝 Query:")
    print(f"  Interests: {interests}")
    print(f"  Duration: {hours}h")
    print(f"  Social mode: {social_mode}")
    print(f"  Intensity: {intensity}\n")
    
    query_text = f"{social_mode} {hours}h walk, {interests}"
    user_embedding, _ = await embedding_service.get_embedding(query_text)
    print(f"✅ Generated user embedding (dim={len(user_embedding)})")
    
    async with async_session_maker() as session:
        scored_pois = await ranking_service.rank_pois(
            session=session,
            user_embedding=user_embedding,
            social_mode=social_mode,
            intensity=intensity,
            top_k=10,
        )
        print(f"✅ Ranked {len(scored_pois)} candidate POIs")
        
        print("\n🏆 Top 5 matches:")
        for poi, score in scored_pois[:5]:
            print(f"  {score:.3f} - {poi.name} ({poi.category})")
        
        candidate_pois = [poi for poi, _ in scored_pois]
        
        optimized_route, total_distance = route_planner.optimize_route(
            start_lat=start_lat,
            start_lon=start_lon,
            pois=candidate_pois,
            available_hours=hours,
        )
        print(f"\n✅ Optimized route: {len(optimized_route)} POIs, {total_distance:.2f}km")
        
        print("\n🎯 Final route:")
        for i, poi in enumerate(optimized_route, 1):
            print(f"  {i}. {poi.name}")
        
        print("\n🤖 Generating LLM explanations...")
        try:
            llm_response = await llm_service.generate_route_explanation(
                route=optimized_route,
                user_interests=interests,
                social_mode=social_mode,
                intensity=intensity,
            )
            print("✅ LLM response generated")
            print(f"\n📄 Summary: {llm_response.get('summary', 'N/A')[:100]}...")
            
            if llm_response.get('atmospheric_description'):
                print(f"\n🌟 Atmosphere: {llm_response['atmospheric_description'][:100]}...")
                
        except Exception as e:
            print(f"⚠️  LLM generation failed: {e}")
            print("   (This is normal if no API key is configured)")
    
    print("\n✅ Sample route generation completed!")


if __name__ == "__main__":
    asyncio.run(generate_sample())