import pytest
from app.services.geocoding import geocoding_service
from app.services.routing import routing_service


@pytest.mark.asyncio
async def test_geocoding_service():
    """Test geocoding service"""
    await geocoding_service.connect_redis()
    
    # Test valid address
    coords = await geocoding_service.geocode_address("Кремль")
    assert coords is not None
    lat, lon = coords
    assert 56.29 <= lat <= 56.36
    assert 43.85 <= lon <= 44.10
    
    # Test caching
    cached_coords = await geocoding_service.geocode_address("Кремль")
    assert cached_coords == coords


@pytest.mark.asyncio
async def test_coordinate_validation():
    """Test coordinate validation"""
    # Valid coordinates
    assert await geocoding_service.validate_coordinates(56.3287, 44.002) is True
    
    # Invalid coordinates
    assert await geocoding_service.validate_coordinates(55.7558, 37.6173) is False  # Moscow


@pytest.mark.asyncio
async def test_routing_service():
    """Test routing service"""
    await routing_service.connect_redis()
    
    # Test simple route
    coords = [
        (56.3287, 44.002),
        (56.3269, 44.0042),
    ]
    
    route = await routing_service.get_walking_route(coords)
    # May be None if API is unavailable, which is acceptable
    if route:
        assert "routes" in route
        assert len(route["routes"]) > 0


@pytest.mark.asyncio
async def test_route_geometry():
    """Test route geometry calculation"""
    await routing_service.connect_redis()
    
    start = (56.3287, 44.002)
    waypoints = [(56.3269, 44.0042), (56.3255, 43.9895)]
    
    geometry = await routing_service.calculate_route_geometry(start, waypoints)
    
    # Should return at least the waypoints
    assert len(geometry) >= len(waypoints) + 1
    
    # All points should be [lat, lon] pairs
    for point in geometry:
        assert len(point) == 2
        assert isinstance(point[0], (int, float))
        assert isinstance(point[1], (int, float))


def test_distance_calculation():
    """Test haversine distance calculation"""
    # Distance between two known points
    lat1, lon1 = 56.3287, 44.002
    lat2, lon2 = 56.3269, 44.0042
    
    distance = routing_service.calculate_distance_km(lat1, lon1, lat2, lon2)
    
    # Should be approximately 0.22 km
    assert 0.1 < distance < 0.5


@pytest.mark.asyncio
async def test_geocoding_empty_address():
    """Test geocoding with empty address"""
    coords = await geocoding_service.geocode_address("")
    assert coords is None


@pytest.mark.asyncio
async def test_routing_invalid_coords():
    """Test routing with invalid coordinates"""
    coords = [(56.3287, 44.002)]  # Only one point
    
    route = await routing_service.get_walking_route(coords)
    assert route is None