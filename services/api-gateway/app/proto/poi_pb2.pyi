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

class GetCategoriesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class GetCategoriesResponse(_message.Message):
    __slots__ = ("categories",)
    CATEGORIES_FIELD_NUMBER: _ClassVar[int]
    categories: _containers.RepeatedCompositeFieldContainer[Category]
    def __init__(self, categories: _Optional[_Iterable[_Union[Category, _Mapping]]] = ...) -> None: ...

class Category(_message.Message):
    __slots__ = ("value", "label", "count")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    COUNT_FIELD_NUMBER: _ClassVar[int]
    value: str
    label: str
    count: int
    def __init__(self, value: _Optional[str] = ..., label: _Optional[str] = ..., count: _Optional[int] = ...) -> None: ...

class CafeSearchRequest(_message.Message):
    __slots__ = ("lat", "lon", "radius_km")
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    RADIUS_KM_FIELD_NUMBER: _ClassVar[int]
    lat: float
    lon: float
    radius_km: float
    def __init__(self, lat: _Optional[float] = ..., lon: _Optional[float] = ..., radius_km: _Optional[float] = ...) -> None: ...

class CafeSearchResponse(_message.Message):
    __slots__ = ("cafes",)
    CAFES_FIELD_NUMBER: _ClassVar[int]
    cafes: _containers.RepeatedCompositeFieldContainer[Cafe]
    def __init__(self, cafes: _Optional[_Iterable[_Union[Cafe, _Mapping]]] = ...) -> None: ...

class Cafe(_message.Message):
    __slots__ = ("id", "name", "lat", "lon", "address", "rubrics", "distance")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    RUBRICS_FIELD_NUMBER: _ClassVar[int]
    DISTANCE_FIELD_NUMBER: _ClassVar[int]
    id: str
    name: str
    lat: float
    lon: float
    address: str
    rubrics: _containers.RepeatedScalarFieldContainer[str]
    distance: float
    def __init__(self, id: _Optional[str] = ..., name: _Optional[str] = ..., lat: _Optional[float] = ..., lon: _Optional[float] = ..., address: _Optional[str] = ..., rubrics: _Optional[_Iterable[str]] = ..., distance: _Optional[float] = ...) -> None: ...

class POI(_message.Message):
    __slots__ = ("id", "name", "lat", "lon", "category", "tags", "description", "avg_visit_minutes", "rating", "embedding", "local_tip", "photo_tip", "address", "social_mode", "intensity_level")
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
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    SOCIAL_MODE_FIELD_NUMBER: _ClassVar[int]
    INTENSITY_LEVEL_FIELD_NUMBER: _ClassVar[int]
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
    address: str
    social_mode: str
    intensity_level: str
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., lat: _Optional[float] = ..., lon: _Optional[float] = ..., category: _Optional[str] = ..., tags: _Optional[_Iterable[str]] = ..., description: _Optional[str] = ..., avg_visit_minutes: _Optional[int] = ..., rating: _Optional[float] = ..., embedding: _Optional[_Iterable[float]] = ..., local_tip: _Optional[str] = ..., photo_tip: _Optional[str] = ..., address: _Optional[str] = ..., social_mode: _Optional[str] = ..., intensity_level: _Optional[str] = ...) -> None: ...
