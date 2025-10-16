from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class GetPOIsRequest(_message.Message):
    __slots__ = ("categories", "with_embeddings")
    CATEGORIES_FIELD_NUMBER: _ClassVar[int]
    WITH_EMBEDDINGS_FIELD_NUMBER: _ClassVar[int]
    categories: _containers.RepeatedScalarFieldContainer[str]
    with_embeddings: bool
    def __init__(self, categories: _Optional[_Iterable[str]] = ..., with_embeddings: bool = ...) -> None: ...

class GetPOIsResponse(_message.Message):
    __slots__ = ("pois",)
    POIS_FIELD_NUMBER: _ClassVar[int]
    pois: _containers.RepeatedCompositeFieldContainer[POI]
    def __init__(self, pois: _Optional[_Iterable[_Union[POI, _Mapping]]] = ...) -> None: ...

class POI(_message.Message):
    __slots__ = ("id", "name", "lat", "lon", "category", "tags", "description", "avg_visit_minutes", "rating", "embedding", "local_tip", "photo_tip")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    AVG_VISIT_MINUTES_FIELD_NUMBER: _ClassVar[int]
    RATING_FIELD_NUMBER: _ClassVar[int]
    EMBEDDING_FIELD_NUMBER: _ClassVar[int]
    LOCAL_TIP_FIELD_NUMBER: _ClassVar[int]
    PHOTO_TIP_FIELD_NUMBER: _ClassVar[int]
    id: int
    name: str
    lat: float
    lon: float
    category: str
    tags: _containers.RepeatedScalarFieldContainer[str]
    description: str
    avg_visit_minutes: int
    rating: float
    embedding: _containers.RepeatedScalarFieldContainer[float]
    local_tip: str
    photo_tip: str
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., lat: _Optional[float] = ..., lon: _Optional[float] = ..., category: _Optional[str] = ..., tags: _Optional[_Iterable[str]] = ..., description: _Optional[str] = ..., avg_visit_minutes: _Optional[int] = ..., rating: _Optional[float] = ..., embedding: _Optional[_Iterable[float]] = ..., local_tip: _Optional[str] = ..., photo_tip: _Optional[str] = ...) -> None: ...

class CoffeeShopRequest(_message.Message):
    __slots__ = ("lat", "lon", "radius_meters", "limit")
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    RADIUS_METERS_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    lat: float
    lon: float
    radius_meters: int
    limit: int
    def __init__(self, lat: _Optional[float] = ..., lon: _Optional[float] = ..., radius_meters: _Optional[int] = ..., limit: _Optional[int] = ...) -> None: ...

class CoffeeShopResponse(_message.Message):
    __slots__ = ("coffee_shops",)
    COFFEE_SHOPS_FIELD_NUMBER: _ClassVar[int]
    coffee_shops: _containers.RepeatedCompositeFieldContainer[CoffeeShop]
    def __init__(self, coffee_shops: _Optional[_Iterable[_Union[CoffeeShop, _Mapping]]] = ...) -> None: ...

class CoffeeShop(_message.Message):
    __slots__ = ("name", "lat", "lon", "rating", "avg_visit_minutes", "description")
    NAME_FIELD_NUMBER: _ClassVar[int]
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    RATING_FIELD_NUMBER: _ClassVar[int]
    AVG_VISIT_MINUTES_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    name: str
    lat: float
    lon: float
    rating: float
    avg_visit_minutes: int
    description: str
    def __init__(self, name: _Optional[str] = ..., lat: _Optional[float] = ..., lon: _Optional[float] = ..., rating: _Optional[float] = ..., avg_visit_minutes: _Optional[int] = ..., description: _Optional[str] = ...) -> None: ...

class CoffeeBreakRequest(_message.Message):
    __slots__ = ("route", "interval_minutes", "preferences")
    ROUTE_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_MINUTES_FIELD_NUMBER: _ClassVar[int]
    PREFERENCES_FIELD_NUMBER: _ClassVar[int]
    route: _containers.RepeatedCompositeFieldContainer[POI]
    interval_minutes: int
    preferences: CoffeePreferences
    def __init__(self, route: _Optional[_Iterable[_Union[POI, _Mapping]]] = ..., interval_minutes: _Optional[int] = ..., preferences: _Optional[_Union[CoffeePreferences, _Mapping]] = ...) -> None: ...

class CoffeePreferences(_message.Message):
    __slots__ = ("enabled", "interval_minutes", "preferred_types")
    ENABLED_FIELD_NUMBER: _ClassVar[int]
    INTERVAL_MINUTES_FIELD_NUMBER: _ClassVar[int]
    PREFERRED_TYPES_FIELD_NUMBER: _ClassVar[int]
    enabled: bool
    interval_minutes: int
    preferred_types: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, enabled: bool = ..., interval_minutes: _Optional[int] = ..., preferred_types: _Optional[_Iterable[str]] = ...) -> None: ...

class CoffeeBreakResponse(_message.Message):
    __slots__ = ("updated_route",)
    UPDATED_ROUTE_FIELD_NUMBER: _ClassVar[int]
    updated_route: _containers.RepeatedCompositeFieldContainer[POI]
    def __init__(self, updated_route: _Optional[_Iterable[_Union[POI, _Mapping]]] = ...) -> None: ...
