from datetime import datetime

from pydantic import Field

from .common import CommonBase


class StoredCredential(CommonBase):
    """
    Represents a session credential persisted in the credential store.
    """

    cookies: dict[str, str] = Field(
        description='Session cookies keyed by cookie name.'
    )
    csrf_token: str | None = Field(
        description='CSRF token bound to the session, if any.'
    )
    updated_at: datetime = Field(
        description='Timestamp the credential was last written at.'
    )
