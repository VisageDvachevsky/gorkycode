from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class RouteExplanationRequest(_message.Message):
    __slots__ = ("pois", "user_interests", "social_mode", "intensity")
    POIS_FIELD_NUMBER: _ClassVar[int]
    USER_INTERESTS_FIELD_NUMBER: _ClassVar[int]
    SOCIAL_MODE_FIELD_NUMBER: _ClassVar[int]
    INTENSITY_FIELD_NUMBER: _ClassVar[int]
    pois: _containers.RepeatedCompositeFieldContainer[POI]
    user_interests: str
    social_mode: str
    intensity: str
    def __init__(self, pois: _Optional[_Iterable[_Union[POI, _Mapping]]] = ..., user_interests: _Optional[str] = ..., social_mode: _Optional[str] = ..., intensity: _Optional[str] = ...) -> None: ...

class POI(_message.Message):
    __slots__ = ("id", "name", "category", "tags", "description", "local_tip", "rating")
    ID_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    CATEGORY_FIELD_NUMBER: _ClassVar[int]
    TAGS_FIELD_NUMBER: _ClassVar[int]
    DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    LOCAL_TIP_FIELD_NUMBER: _ClassVar[int]
    RATING_FIELD_NUMBER: _ClassVar[int]
    id: int
    name: str
    category: str
    tags: _containers.RepeatedScalarFieldContainer[str]
    description: str
    local_tip: str
    rating: float
    def __init__(self, id: _Optional[int] = ..., name: _Optional[str] = ..., category: _Optional[str] = ..., tags: _Optional[_Iterable[str]] = ..., description: _Optional[str] = ..., local_tip: _Optional[str] = ..., rating: _Optional[float] = ...) -> None: ...

class RouteExplanationResponse(_message.Message):
    __slots__ = ("summary", "explanations", "notes", "atmospheric_description", "latency_ms")
    SUMMARY_FIELD_NUMBER: _ClassVar[int]
    EXPLANATIONS_FIELD_NUMBER: _ClassVar[int]
    NOTES_FIELD_NUMBER: _ClassVar[int]
    ATMOSPHERIC_DESCRIPTION_FIELD_NUMBER: _ClassVar[int]
    LATENCY_MS_FIELD_NUMBER: _ClassVar[int]
    summary: str
    explanations: _containers.RepeatedCompositeFieldContainer[Explanation]
    notes: _containers.RepeatedScalarFieldContainer[str]
    atmospheric_description: str
    latency_ms: float
    def __init__(self, summary: _Optional[str] = ..., explanations: _Optional[_Iterable[_Union[Explanation, _Mapping]]] = ..., notes: _Optional[_Iterable[str]] = ..., atmospheric_description: _Optional[str] = ..., latency_ms: _Optional[float] = ...) -> None: ...

class Explanation(_message.Message):
    __slots__ = ("poi_id", "why", "tip")
    POI_ID_FIELD_NUMBER: _ClassVar[int]
    WHY_FIELD_NUMBER: _ClassVar[int]
    TIP_FIELD_NUMBER: _ClassVar[int]
    poi_id: int
    why: str
    tip: str
    def __init__(self, poi_id: _Optional[int] = ..., why: _Optional[str] = ..., tip: _Optional[str] = ...) -> None: ...

class TaskResponse(_message.Message):
    __slots__ = ("task_id", "status")
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    STATUS_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    status: str
    def __init__(self, task_id: _Optional[str] = ..., status: _Optional[str] = ...) -> None: ...

class TaskStatusRequest(_message.Message):
    __slots__ = ("task_id",)
    TASK_ID_FIELD_NUMBER: _ClassVar[int]
    task_id: str
    def __init__(self, task_id: _Optional[str] = ...) -> None: ...

class TaskStatusResponse(_message.Message):
    __slots__ = ("status", "result", "error")
    STATUS_FIELD_NUMBER: _ClassVar[int]
    RESULT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    status: str
    result: RouteExplanationResponse
    error: str
    def __init__(self, status: _Optional[str] = ..., result: _Optional[_Union[RouteExplanationResponse, _Mapping]] = ..., error: _Optional[str] = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("healthy", "provider", "model", "active_tasks")
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    PROVIDER_FIELD_NUMBER: _ClassVar[int]
    MODEL_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_TASKS_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    provider: str
    model: str
    active_tasks: int
    def __init__(self, healthy: bool = ..., provider: _Optional[str] = ..., model: _Optional[str] = ..., active_tasks: _Optional[int] = ...) -> None: ...
