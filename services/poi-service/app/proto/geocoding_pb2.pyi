from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class GeocodeRequest(_message.Message):
    __slots__ = ("address", "city")
    ADDRESS_FIELD_NUMBER: _ClassVar[int]
    CITY_FIELD_NUMBER: _ClassVar[int]
    address: str
    city: str
    def __init__(self, address: _Optional[str] = ..., city: _Optional[str] = ...) -> None: ...

class GeocodeResponse(_message.Message):
    __slots__ = ("success", "lat", "lon", "formatted_address")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    FORMATTED_ADDRESS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    lat: float
    lon: float
    formatted_address: str
    def __init__(self, success: bool = ..., lat: _Optional[float] = ..., lon: _Optional[float] = ..., formatted_address: _Optional[str] = ...) -> None: ...

class CoordinateValidationRequest(_message.Message):
    __slots__ = ("lat", "lon")
    LAT_FIELD_NUMBER: _ClassVar[int]
    LON_FIELD_NUMBER: _ClassVar[int]
    lat: float
    lon: float
    def __init__(self, lat: _Optional[float] = ..., lon: _Optional[float] = ...) -> None: ...

class CoordinateValidationResponse(_message.Message):
    __slots__ = ("valid", "reason")
    VALID_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    valid: bool
    reason: str
    def __init__(self, valid: bool = ..., reason: _Optional[str] = ...) -> None: ...
