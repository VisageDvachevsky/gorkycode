from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Iterable as _Iterable, Mapping as _Mapping, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RouteExplanationRequest(_message.Message):
    __slots__ = ("route", "user_interests", "social_mode", "intensity")
    ROUTE_FIELD_NUMBER: _ClassVar[int]
    USER_INTERESTS_FIELD_NUMBER: _ClassVar[int]
    SOCIAL_MODE_FIELD_NUMBER: _ClassVar[int]
    INTENSITY_FIELD_NUMBER: _ClassVar[int]
    route: _containers.RepeatedCompositeFieldContainer[POIContext]
    user_interests: str
    social_mode: str
    intensity: str
    def __init__(self, route: _Optional[_Iterable[_Union[POIContext, _Mapping]]] = ..., user_interests: _Optional[str] = ..., social_mode: _Optional[str] = ..., intensity: _Optional[str] = ...) -> None: ...

class POIContext(_message.Message):
    __slots__ = ("id", "name", "description", "category", "tags", "local_tip")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    LOCAL_TIP_FIELD_NUMBER: _ClassVar[int]
    id: int
    name: str
    description: str
    category: str
    tags: _containers.RepeatedScalarFieldContainer[str]
    local_tip: str
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., description: _Optional[str] = ..., category: _Optional[str] = ..., tags: _Optional[_Iterable[str]] = ..., local_tip: _Optional[str] = ...) -> None: ...

class RouteExplanationResponse(_message.Message):
    __slots__ = ("summary", "explanations", "notes", "atmospheric_description")
    SUMMARY_FIELD_NUMBER: _ClassVar[int]
    EXPLANATIONS_FIELD_NUMBER: _ClassVar[int]
    NOTES_FIELD_NUMBER: _ClassVar[int]
    ATMOSPHERIC_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    summary: str
    explanations: _containers.RepeatedCompositeFieldContainer[POIExplanation]
    notes: _containers.RepeatedScalarFieldContainer[str]
    atmospheric_description: str
    def __init__(self, summary: _Optional[str] = ..., explanations: _Optional[_Iterable[_Union[POIExplanation, _Mapping]]] = ..., notes: _Optional[_Iterable[str]] = ..., atmospheric_description: _Optional[str] = ...) -> None: ...

class POIExplanation(_message.Message):
    __slots__ = ("poi_id", "why", "tip")
    POI_ID_FIELD_NUMBER: _ClassVar[int]
    WHY_FIELD_NUMBER: _ClassVar[int]
    TIP_FIELD_NUMBER: _ClassVar[int]
    poi_id: int
    why: str
    tip: str
    def __init__(self, poi_id: _Optional[int] = ..., why: _Optional[str] = ..., tip: _Optional[str] = ...) -> None: ...
