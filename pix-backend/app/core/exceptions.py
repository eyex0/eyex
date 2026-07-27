from __future__ import annotations


class AppError(Exception):
    def __init__(self, message: str, status_code: int = 500, detail: str | None = None):
        self.message = message
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.message)


# Backward-compatible aliases for existing imports.
AppException = AppError


class NotFoundError(AppError):
    def __init__(self, resource: str = "Resource"):
        super().__init__(f"{resource} not found", status_code=404)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)


class ValidationError(AppError):
    def __init__(self, detail: str):
        super().__init__("Validation error", status_code=422, detail=detail)


# Backward-compatible aliases.
NotFoundException = NotFoundError
UnauthorizedException = UnauthorizedError
ForbiddenException = ForbiddenError
ValidationException = ValidationError
