from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GeocodeRequest(_message.Message):
    __slots__ = ("address", "hint")
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    HINT_FIELD_NUMBER: _ClassVar[int]
    address: str
    hint: Location
    def __init__(self, address: _Optional[str] = ..., hint: _Optional[_Union[Location, _Mapping]] = ...) -> None: ...

class Location(_message.Message):
    __slots__ = ("lat", "lon")
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    lat: float
    lon: float
    def __init__(self, lat: _Optional[float] = ..., lon: _Optional[float] = ...) -> None: ...

class GeocodeResponse(_message.Message):
    __slots__ = ("success", "location", "error")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    success: bool
    location: Location
    error: str
    def __init__(self, success: bool = ..., location: _Optional[_Union[Location, _Mapping]] = ..., error: _Optional[str] = ...) -> None: ...

class ReverseGeocodeRequest(_message.Message):
    __slots__ = ("location",)
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    location: Location
    def __init__(self, location: _Optional[_Union[Location, _Mapping]] = ...) -> None: ...

class ReverseGeocodeResponse(_message.Message):
    __slots__ = ("address",)
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    address: str
    def __init__(self, address: _Optional[str] = ...) -> None: ...

class CafeSearchRequest(_message.Message):
    __slots__ = ("location", "radius_km", "limit", "filters")
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    RADIUS_KM_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    FILTERS_FIELD_NUMBER: _ClassVar[int]
    location: Location
    radius_km: float
    limit: int
    filters: CafeFilters
    def __init__(self, location: _Optional[_Union[Location, _Mapping]] = ..., radius_km: _Optional[float] = ..., limit: _Optional[int] = ..., filters: _Optional[_Union[CafeFilters, _Mapping]] = ...) -> None: ...

class CafeFilters(_message.Message):
    __slots__ = ("cuisine", "dietary", "outdoor_seating", "wifi")
    CUISINE_FIELD_NUMBER: _ClassVar[int]
    DIETARY_FIELD_NUMBER: _ClassVar[int]
    OUTDOOR_SEATING_FIELD_NUMBER: _ClassVar[int]
    WIFI_FIELD_NUMBER: _ClassVar[int]
    cuisine: str
    dietary: str
    outdoor_seating: bool
    wifi: bool
    def __init__(self, cuisine: _Optional[str] = ..., dietary: _Optional[str] = ..., outdoor_seating: bool = ..., wifi: bool = ...) -> None: ...

class CafeSearchResponse(_message.Message):
    __slots__ = ("cafes",)
    CAFES_FIELD_NUMBER: _ClassVar[int]
    cafes: _containers.RepeatedCompositeFieldContainer[Cafe]
    def __init__(self, cafes: _Optional[_Iterable[_Union[Cafe, _Mapping]]] = ...) -> None: ...

class Cafe(_message.Message):
    __slots__ = ("id", "name", "location", "address", "rubrics", "rating")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    RUBRICS_FIELD_NUMBER: _ClassVar[int]
    RATING_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    location: Location
    address: str
    rubrics: _containers.RepeatedScalarFieldContainer[str]
    rating: float
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., location: _Optional[_Union[Location, _Mapping]] = ..., address: _Optional[str] = ..., rubrics: _Optional[_Iterable[str]] = ..., rating: _Optional[float] = ...) -> None: ...

class WalkingRouteRequest(_message.Message):
    __slots__ = ("waypoints",)
    WAYPOINTS_FIELD_NUMBER: _ClassVar[int]
    waypoints: _containers.RepeatedCompositeFieldContainer[Location]
    def __init__(self, waypoints: _Optional[_Iterable[_Union[Location, _Mapping]]] = ...) -> None: ...

class WalkingRouteResponse(_message.Message):
    __slots__ = ("geometry", "distance_km", "duration_minutes")
    GEOMETRY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_KM_FIELD_NUMBER: _ClassVar[int]
    DURATION_MINUTES_FIELD_NUMBER: _ClassVar[int]
    geometry: _containers.RepeatedCompositeFieldContainer[Location]
    distance_km: float
    duration_minutes: int
    def __init__(self, geometry: _Optional[_Iterable[_Union[Location, _Mapping]]] = ..., distance_km: _Optional[float] = ..., duration_minutes: _Optional[int] = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("healthy", "api_key_valid", "requests_today")
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    API_KEY_VALID_FIELD_NUMBER: _ClassVar[int]
    REQUESTS_TODAY_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    api_key_valid: bool
    requests_today: int
    def __init__(self, healthy: bool = ..., api_key_valid: bool = ..., requests_today: _Optional[int] = ...) -> None: ...
