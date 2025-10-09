import pytest
from httpx import AsyncClient
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.asyncio
async def test_generate_embedding_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/embedding/generate",
            json={"text": "street-art panoramas coffee"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "embedding" in data
        assert isinstance(data["embedding"], list)
        assert len(data["embedding"]) > 0


@pytest.mark.asyncio
async def test_plan_route_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/route/plan",
            json={
                "interests": "architecture history panorama",
                "hours": 2.0,
                "start_lat": 56.3287,
                "start_lon": 44.002,
                "social_mode": "solo",
                "intensity": "medium"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "route" in data
        assert "summary" in data
        assert isinstance(data["route"], list)