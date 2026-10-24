"""Authorization for write operations.

This is a deliberately small guard for the first module: a shared admin API key sent
in the `X-API-Key` header. When `ADMIN_API_KEY` is empty (local development only) the
guard is open; the application refuses to start in production without a key.

Replace this with user accounts (hashed passwords, roles, tokens) when the attendance
modules introduce lecturers and other roles; routes only depend on `require_admin`.
"""

import secrets
from typing import Annotated

from fastapi import Depends
from fastapi.security import APIKeyHeader

from app.core.config import Settings, get_settings
from app.core.errors import UnauthorizedError

# Registered as an OpenAPI security scheme, so Swagger UI's "Authorize" button can send it.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False, description="Admin API key")


def require_admin(
    settings: Annotated[Settings, Depends(get_settings)],
    x_api_key: Annotated[str | None, Depends(api_key_header)],
) -> None:
    expected = settings.admin_api_key
    if not expected:
        return
    if not x_api_key or not secrets.compare_digest(x_api_key.encode(), expected.encode()):
        raise UnauthorizedError(
            "A valid admin API key is required for this action. Set it on the Settings page.",
            code="invalid_api_key",
        )


AdminRequired = Depends(require_admin)
