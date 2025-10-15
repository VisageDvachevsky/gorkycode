from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class EmbeddingRequest(_message.Message):
    __slots__ = ("text", "use_cache")
    TEXT_FIELD_NUMBER: _ClassVar[int]
    USE_CACHE_FIELD_NUMBER: _ClassVar[int]
    text: str
    use_cache: bool
    def __init__(self, text: _Optional[str] = ..., use_cache: bool = ...) -> None: ...

class EmbeddingResponse(_message.Message):
    __slots__ = ("embedding", "from_cache", "dimension", "latency_ms")
    EMBEDDING_FIELD_NUMBER: _ClassVar[int]
    FROM_CACHE_FIELD_NUMBER: _ClassVar[int]
    DIMENSION_FIELD_NUMBER: _ClassVar[int]
    LATENCY_MS_FIELD_NUMBER: _ClassVar[int]
    embedding: _containers.RepeatedScalarFieldContainer[float]
    from_cache: bool
    dimension: int
    latency_ms: float
    def __init__(self, embedding: _Optional[_Iterable[float]] = ..., from_cache: bool = ..., dimension: _Optional[int] = ..., latency_ms: _Optional[float] = ...) -> None: ...

class EmbeddingBatchRequest(_message.Message):
    __slots__ = ("texts", "use_cache")
    TEXTS_FIELD_NUMBER: _ClassVar[int]
    USE_CACHE_FIELD_NUMBER: _ClassVar[int]
    texts: _containers.RepeatedScalarFieldContainer[str]
    use_cache: bool
    def __init__(self, texts: _Optional[_Iterable[str]] = ..., use_cache: bool = ...) -> None: ...

class EmbeddingBatchResponse(_message.Message):
    __slots__ = ("results", "total_latency_ms")
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_LATENCY_MS_FIELD_NUMBER: _ClassVar[int]
    results: _containers.RepeatedCompositeFieldContainer[EmbeddingResult]
    total_latency_ms: float
    def __init__(self, results: _Optional[_Iterable[_Union[EmbeddingResult, _Mapping]]] = ..., total_latency_ms: _Optional[float] = ...) -> None: ...

class EmbeddingResult(_message.Message):
    __slots__ = ("embedding", "from_cache")
    EMBEDDING_FIELD_NUMBER: _ClassVar[int]
    FROM_CACHE_FIELD_NUMBER: _ClassVar[int]
    embedding: _containers.RepeatedScalarFieldContainer[float]
    from_cache: bool
    def __init__(self, embedding: _Optional[_Iterable[float]] = ..., from_cache: bool = ...) -> None: ...

class SimilarityRequest(_message.Message):
    __slots__ = ("vector1", "vector2")
    VECTOR1_FIELD_NUMBER: _ClassVar[int]
    VECTOR2_FIELD_NUMBER: _ClassVar[int]
    vector1: _containers.RepeatedScalarFieldContainer[float]
    vector2: _containers.RepeatedScalarFieldContainer[float]
    def __init__(self, vector1: _Optional[_Iterable[float]] = ..., vector2: _Optional[_Iterable[float]] = ...) -> None: ...

class SimilarityResponse(_message.Message):
    __slots__ = ("similarity",)
    SIMILARITY_FIELD_NUMBER: _ClassVar[int]
    similarity: float
    def __init__(self, similarity: _Optional[float] = ...) -> None: ...

class HealthCheckRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class HealthCheckResponse(_message.Message):
    __slots__ = ("healthy", "model_name", "model_dimension", "cache_size")
    HEALTHY_FIELD_NUMBER: _ClassVar[int]
    MODEL_NAME_FIELD_NUMBER: _ClassVar[int]
    MODEL_DIMENSION_FIELD_NUMBER: _ClassVar[int]
    CACHE_SIZE_FIELD_NUMBER: _ClassVar[int]
    healthy: bool
    model_name: str
    model_dimension: int
    cache_size: int
    def __init__(self, healthy: bool = ..., model_name: _Optional[str] = ..., model_dimension: _Optional[int] = ..., cache_size: _Optional[int] = ...) -> None: ...
