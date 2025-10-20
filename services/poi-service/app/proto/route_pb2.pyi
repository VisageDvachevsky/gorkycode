from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

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
    __slots__ = ("optimized_route", "total_distance_km", "total_minutes", "legs", "total_walking_distance_km", "total_transit_distance_km")
    OPTIMIZED_ROUTE_FIELD_NUMBER: _ClassVar[int]
    TOTAL_DISTANCE_KM_FIELD_NUMBER: _ClassVar[int]
    TOTAL_MINUTES_FIELD_NUMBER: _ClassVar[int]
    LEGS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_WALKING_DISTANCE_KM_FIELD_NUMBER: _ClassVar[int]
    TOTAL_TRANSIT_DISTANCE_KM_FIELD_NUMBER: _ClassVar[int]
    optimized_route: _containers.RepeatedCompositeFieldContainer[POIInfo]
    total_distance_km: float
    total_minutes: int
    legs: _containers.RepeatedCompositeFieldContainer[RouteLeg]
    total_walking_distance_km: float
    total_transit_distance_km: float
    def __init__(self, optimized_route: _Optional[_Iterable[_Union[POIInfo, _Mapping]]] = ..., total_distance_km: _Optional[float] = ..., total_minutes: _Optional[int] = ..., legs: _Optional[_Iterable[_Union[RouteLeg, _Mapping]]] = ..., total_walking_distance_km: _Optional[float] = ..., total_transit_distance_km: _Optional[float] = ...) -> None: ...

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

class LegManeuver(_message.Message):
    __slots__ = ("instruction", "street_name", "distance_m", "duration_sec")
    INSTRUCTION_FIELD_NUMBER: _ClassVar[int]
    STREET_NAME_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_M_FIELD_NUMBER: _ClassVar[int]
    DURATION_SEC_FIELD_NUMBER: _ClassVar[int]
    instruction: str
    street_name: str
    distance_m: float
    duration_sec: float
    def __init__(self, instruction: _Optional[str] = ..., street_name: _Optional[str] = ..., distance_m: _Optional[float] = ..., duration_sec: _Optional[float] = ...) -> None: ...

class TransitStop(_message.Message):
    __slots__ = ("name", "side", "position")
    NAME_FIELD_NUMBER: _ClassVar[int]
    SIDE_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    name: str
    side: str
    position: Coordinate
    def __init__(self, name: _Optional[str] = ..., side: _Optional[str] = ..., position: _Optional[_Union[Coordinate, _Mapping]] = ...) -> None: ...

class TransitLegDetails(_message.Message):
    __slots__ = ("provider", "line_name", "vehicle_type", "direction", "vehicle_number", "summary", "boarding", "alighting", "departure_time", "arrival_time", "notes", "walk_to_board_meters", "walk_from_alight_meters")
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    LINE_NAME_FIELD_NUMBER: _ClassVar[int]
    VEHICLE_TYPE_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    VEHICLE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    SUMMARY_FIELD_NUMBER: _ClassVar[int]
    BOARDING_FIELD_NUMBER: _ClassVar[int]
    ALIGHTING_FIELD_NUMBER: _ClassVar[int]
    DEPARTURE_TIME_FIELD_NUMBER: _ClassVar[int]
    ARRIVAL_TIME_FIELD_NUMBER: _ClassVar[int]
    NOTES_FIELD_NUMBER: _ClassVar[int]
    WALK_TO_BOARD_METERS_FIELD_NUMBER: _ClassVar[int]
    WALK_FROM_ALIGHT_METERS_FIELD_NUMBER: _ClassVar[int]
    provider: str
    line_name: str
    vehicle_type: str
    direction: str
    vehicle_number: str
    summary: str
    boarding: TransitStop
    alighting: TransitStop
    departure_time: str
    arrival_time: str
    notes: str
    walk_to_board_meters: float
    walk_from_alight_meters: float
    def __init__(self, provider: _Optional[str] = ..., line_name: _Optional[str] = ..., vehicle_type: _Optional[str] = ..., direction: _Optional[str] = ..., vehicle_number: _Optional[str] = ..., summary: _Optional[str] = ..., boarding: _Optional[_Union[TransitStop, _Mapping]] = ..., alighting: _Optional[_Union[TransitStop, _Mapping]] = ..., departure_time: _Optional[str] = ..., arrival_time: _Optional[str] = ..., notes: _Optional[str] = ..., walk_to_board_meters: _Optional[float] = ..., walk_from_alight_meters: _Optional[float] = ...) -> None: ...

class RouteLeg(_message.Message):
    __slots__ = ("start", "end", "distance_km", "duration_minutes", "mode", "maneuvers", "transit")
    START_FIELD_NUMBER: _ClassVar[int]
    END_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_KM_FIELD_NUMBER: _ClassVar[int]
    DURATION_MINUTES_FIELD_NUMBER: _ClassVar[int]
    MODE_FIELD_NUMBER: _ClassVar[int]
    MANEUVERS_FIELD_NUMBER: _ClassVar[int]
    TRANSIT_FIELD_NUMBER: _ClassVar[int]
    start: Coordinate
    end: Coordinate
    distance_km: float
    duration_minutes: float
    mode: str
    maneuvers: _containers.RepeatedCompositeFieldContainer[LegManeuver]
    transit: TransitLegDetails
    def __init__(self, start: _Optional[_Union[Coordinate, _Mapping]] = ..., end: _Optional[_Union[Coordinate, _Mapping]] = ..., distance_km: _Optional[float] = ..., duration_minutes: _Optional[float] = ..., mode: _Optional[str] = ..., maneuvers: _Optional[_Iterable[_Union[LegManeuver, _Mapping]]] = ..., transit: _Optional[_Union[TransitLegDetails, _Mapping]] = ...) -> None: ...

class RouteGeometryResponse(_message.Message):
    __slots__ = ("geometry", "total_distance_km")
    GEOMETRY_FIELD_NUMBER: _ClassVar[int]
    TOTAL_DISTANCE_KM_FIELD_NUMBER: _ClassVar[int]
    geometry: _containers.RepeatedCompositeFieldContainer[Coordinate]
    total_distance_km: float
    def __init__(self, geometry: _Optional[_Iterable[_Union[Coordinate, _Mapping]]] = ..., total_distance_km: _Optional[float] = ...) -> None: ...
