from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RankingRequest(_message.Message):
    __slots__ = ("user_embedding", "social_mode", "intensity", "top_k", "categories_filter")
    USER_EMBEDDING_FIELD_NUMBER: _ClassVar[int]
    SOCIAL_MODE_FIELD_NUMBER: _ClassVar[int]
    INTENSITY_FIELD_NUMBER: _ClassVar[int]
    TOP_K_FIELD_NUMBER: _ClassVar[int]
    CATEGORIES_FILTER_FIELD_NUMBER: _ClassVar[int]
    user_embedding: _containers.RepeatedScalarFieldContainer[float]
    social_mode: str
    intensity: str
    top_k: int
    categories_filter: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, user_embedding: _Optional[_Iterable[float]] = ..., social_mode: _Optional[str] = ..., intensity: _Optional[str] = ..., top_k: _Optional[int] = ..., categories_filter: _Optional[_Iterable[str]] = ...) -> None: ...

class RankingResponse(_message.Message):
    __slots__ = ("scored_pois",)
    SCORED_POIS_FIELD_NUMBER: _ClassVar[int]
    scored_pois: _containers.RepeatedCompositeFieldContainer[ScoredPOI]
    def __init__(self, scored_pois: _Optional[_Iterable[_Union[ScoredPOI, _Mapping]]] = ...) -> None: ...

class ScoredPOI(_message.Message):
    __slots__ = ("poi_id", "name", "lat", "lon", "category", "tags", "description", "avg_visit_minutes", "rating", "score", "embedding")
    POI_ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    AVG_VISIT_MINUTES_FIELD_NUMBER: _ClassVar[int]
    RATING_FIELD_NUMBER: _ClassVar[int]
    SCORE_FIELD_NUMBER: _ClassVar[int]
    EMBEDDING_FIELD_NUMBER: _ClassVar[int]
    poi_id: int
    name: str
    lat: float
    lon: float
    category: str
    tags: _containers.RepeatedScalarFieldContainer[str]
    description: str
    avg_visit_minutes: int
    rating: float
    score: float
    embedding: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, poi_id: _Optional[int] = ..., name: _Optional[str] = ..., lat: _Optional[float] = ..., lon: _Optional[float] = ..., category: _Optional[str] = ..., tags: _Optional[_Iterable[str]] = ..., description: _Optional[str] = ..., avg_visit_minutes: _Optional[int] = ..., rating: _Optional[float] = ..., score: _Optional[float] = ..., embedding: _Optional[_Iterable[float]] = ...) -> None: ...
