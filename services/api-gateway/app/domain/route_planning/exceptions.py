from __future__ import annotations


class RoutePlanningError(Exception):
    def __init__(self, message: str, status_code: int = 500) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


class ExternalServiceError(RoutePlanningError):
    def __init__(self, message: str, status_code: int = 503) -> None:
        super().__init__(message, status_code=status_code)
