from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RouteOptimizationRequest(_message.Message):
    __slots__ = ("start_lat", "start_lon", "pois", "available_hours")
    START_LAT_FIELD_NUMBER: _ClassVar[int]
    START_LON_FIELD_NUMBER: _ClassVar[int]
    POIS_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_HOURS_FIELD_NUMBER: _ClassVar[int]
    start_lat: float
    start_lon: float
    pois: _containers.RepeatedCompositeFieldContainer[POIInfo]
    available_hours: float
    def __init__(self, start_lat: _Optional[float] = ..., start_lon: _Optional[float] = ..., pois: _Optional[_Iterable[_Union[POIInfo, _Mapping]]] = ..., available_hours: _Optional[float] = ...) -> None: ...

class POIInfo(_message.Message):
    __slots__ = ("id", "name", "lat", "lon", "avg_visit_minutes", "rating")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    AVG_VISIT_MINUTES_FIELD_NUMBER: _ClassVar[int]
    RATING_FIELD_NUMBER: _ClassVar[int]
    id: int
    name: str
    lat: float
    lon: float
    avg_visit_minutes: int
    rating: float
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., lat: _Optional[float] = ..., lon: _Optional[float] = ..., avg_visit_minutes: _Optional[int] = ..., rating: _Optional[float] = ...) -> None: ...

class RouteOptimizationResponse(_message.Message):
    __slots__ = ("optimized_route", "total_distance_km", "total_minutes")
    OPTIMIZED_ROUTE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_DISTANCE_KM_FIELD_NUMBER: _ClassVar[int]
    TOTAL_MINUTES_FIELD_NUMBER: _ClassVar[int]
    optimized_route: _containers.RepeatedCompositeFieldContainer[POIInfo]
    total_distance_km: float
    total_minutes: int
    def __init__(self, optimized_route: _Optional[_Iterable[_Union[POIInfo, _Mapping]]] = ..., total_distance_km: _Optional[float] = ..., total_minutes: _Optional[int] = ...) -> None: ...

class RouteGeometryRequest(_message.Message):
    __slots__ = ("start_lat", "start_lon", "waypoints")
    START_LAT_FIELD_NUMBER: _ClassVar[int]
    START_LON_FIELD_NUMBER: _ClassVar[int]
    WAYPOINTS_FIELD_NUMBER: _ClassVar[int]
    start_lat: float
    start_lon: float
    waypoints: _containers.RepeatedCompositeFieldContainer[Coordinate]
    def __init__(self, start_lat: _Optional[float] = ..., start_lon: _Optional[float] = ..., waypoints: _Optional[_Iterable[_Union[Coordinate, _Mapping]]] = ...) -> None: ...

class Coordinate(_message.Message):
    __slots__ = ("lat", "lon")
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    lat: float
    lon: float
    def __init__(self, lat: _Optional[float] = ..., lon: _Optional[float] = ...) -> None: ...

class RouteGeometryResponse(_message.Message):
    __slots__ = ("geometry", "total_distance_km")
    GEOMETRY_FIELD_NUMBER: _ClassVar[int]
    TOTAL_DISTANCE_KM_FIELD_NUMBER: _ClassVar[int]
    geometry: _containers.RepeatedCompositeFieldContainer[Coordinate]
    total_distance_km: float
    def __init__(self, geometry: _Optional[_Iterable[_Union[Coordinate, _Mapping]]] = ..., total_distance_km: _Optional[float] = ...) -> None: ...
