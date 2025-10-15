from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class OptimizeRouteRequest(_message.Message):
    __slots__ = ("start", "pois", "available_hours", "optimization_strategy")
    START_FIELD_NUMBER: _ClassVar[int]
    POIS_FIELD_NUMBER: _ClassVar[int]
    AVAILABLE_HOURS_FIELD_NUMBER: _ClassVar[int]
    OPTIMIZATION_STRATEGY_FIELD_NUMBER: _ClassVar[int]
    start: Location
    pois: _containers.RepeatedCompositeFieldContainer[POILocation]
    available_hours: float
    optimization_strategy: str
    def __init__(self, start: _Optional[_Union[Location, _Mapping]] = ..., pois: _Optional[_Iterable[_Union[POILocation, _Mapping]]] = ..., available_hours: _Optional[float] = ..., optimization_strategy: _Optional[str] = ...) -> None: ...

class Location(_message.Message):
    __slots__ = ("lat", "lon")
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    lat: float
    lon: float
    def __init__(self, lat: _Optional[float] = ..., lon: _Optional[float] = ...) -> None: ...

class POILocation(_message.Message):
    __slots__ = ("id", "lat", "lon", "avg_visit_minutes")
    ID_FIELD_NUMBER: _ClassVar[int]
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    AVG_VISIT_MINUTES_FIELD_NUMBER: _ClassVar[int]
    id: int
    lat: float
    lon: float
    avg_visit_minutes: int
    def __init__(self, id: _Optional[int] = ..., lat: _Optional[float] = ..., lon: _Optional[float] = ..., avg_visit_minutes: _Optional[int] = ...) -> None: ...

class OptimizeRouteResponse(_message.Message):
    __slots__ = ("poi_order", "total_distance_km", "total_time_minutes", "algorithm_used", "optimization_score")
    POI_ORDER_FIELD_NUMBER: _ClassVar[int]
    TOTAL_DISTANCE_KM_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TIME_MINUTES_FIELD_NUMBER: _ClassVar[int]
    ALGORITHM_USED_FIELD_NUMBER: _ClassVar[int]
    OPTIMIZATION_SCORE_FIELD_NUMBER: _ClassVar[int]
    poi_order: _containers.RepeatedScalarFieldContainer[int]
    total_distance_km: float
    total_time_minutes: int
    algorithm_used: str
    optimization_score: float
    def __init__(self, poi_order: _Optional[_Iterable[int]] = ..., total_distance_km: _Optional[float] = ..., total_time_minutes: _Optional[int] = ..., algorithm_used: _Optional[str] = ..., optimization_score: _Optional[float] = ...) -> None: ...

class RouteGeometryRequest(_message.Message):
    __slots__ = ("waypoints", "transport_type")
    WAYPOINTS_FIELD_NUMBER: _ClassVar[int]
    TRANSPORT_TYPE_FIELD_NUMBER: _ClassVar[int]
    waypoints: _containers.RepeatedCompositeFieldContainer[Location]
    transport_type: str
    def __init__(self, waypoints: _Optional[_Iterable[_Union[Location, _Mapping]]] = ..., transport_type: _Optional[str] = ...) -> None: ...

class RouteGeometryResponse(_message.Message):
    __slots__ = ("geometry", "distance_km", "duration_minutes")
    GEOMETRY_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_KM_FIELD_NUMBER: _ClassVar[int]
    DURATION_MINUTES_FIELD_NUMBER: _ClassVar[int]
    geometry: _containers.RepeatedCompositeFieldContainer[Location]
    distance_km: float
    duration_minutes: int
    def __init__(self, geometry: _Optional[_Iterable[_Union[Location, _Mapping]]] = ..., distance_km: _Optional[float] = ..., duration_minutes: _Optional[int] = ...) -> None: ...

class DistanceMatrixRequest(_message.Message):
    __slots__ = ("sources", "targets", "transport_type")
    SOURCES_FIELD_NUMBER: _ClassVar[int]
    TARGETS_FIELD_NUMBER: _ClassVar[int]
    TRANSPORT_TYPE_FIELD_NUMBER: _ClassVar[int]
    sources: _containers.RepeatedCompositeFieldContainer[Location]
    targets: _containers.RepeatedCompositeFieldContainer[Location]
    transport_type: str
    def __init__(self, sources: _Optional[_Iterable[_Union[Location, _Mapping]]] = ..., targets: _Optional[_Iterable[_Union[Location, _Mapping]]] = ..., transport_type: _Optional[str] = ...) -> None: ...

class DistanceMatrixResponse(_message.Message):
    __slots__ = ("matrix",)
    MATRIX_FIELD_NUMBER: _ClassVar[int]
    matrix: _containers.RepeatedCompositeFieldContainer[Row]
    def __init__(self, matrix: _Optional[_Iterable[_Union[Row, _Mapping]]] = ...) -> None: ...

class Row(_message.Message):
    __slots__ = ("distances_km",)
    DISTANCES_KM_FIELD_NUMBER: _ClassVar[int]
    distances_km: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, distances_km: _Optional[_Iterable[float]] = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("healthy", "version")
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    VERSION_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    version: str
    def __init__(self, healthy: bool = ..., version: _Optional[str] = ...) -> None: ...
