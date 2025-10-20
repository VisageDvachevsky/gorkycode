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
    __slots__ = ("vector", "from_cache", "dimension")
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    FROM_CACHE_FIELD_NUMBER: _ClassVar[int]
    DIMENSION_FIELD_NUMBER: _ClassVar[int]
    vector: _containers.RepeatedScalarFieldContainer[float]
    from_cache: bool
    dimension: int
    def __init__(self, vector: _Optional[_Iterable[float]] = ..., from_cache: bool = ..., dimension: _Optional[int] = ...) -> None: ...

class BatchEmbeddingRequest(_message.Message):
    __slots__ = ("texts", "use_cache")
    TEXTS_FIELD_NUMBER: _ClassVar[int]
    USE_CACHE_FIELD_NUMBER: _ClassVar[int]
    texts: _containers.RepeatedScalarFieldContainer[str]
    use_cache: bool
    def __init__(self, texts: _Optional[_Iterable[str]] = ..., use_cache: bool = ...) -> None: ...

class BatchEmbeddingResponse(_message.Message):
    __slots__ = ("vectors",)
    VECTORS_FIELD_NUMBER: _ClassVar[int]
    vectors: _containers.RepeatedCompositeFieldContainer[EmbeddingVector]
    def __init__(self, vectors: _Optional[_Iterable[_Union[EmbeddingVector, _Mapping]]] = ...) -> None: ...

class EmbeddingVector(_message.Message):
    __slots__ = ("vector", "from_cache")
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    FROM_CACHE_FIELD_NUMBER: _ClassVar[int]
    vector: _containers.RepeatedScalarFieldContainer[float]
    from_cache: bool
    def __init__(self, vector: _Optional[_Iterable[float]] = ..., from_cache: bool = ...) -> None: ...
