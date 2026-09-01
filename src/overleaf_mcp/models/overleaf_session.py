from datetime import datetime

from pydantic import Field

from .common import CommonBase


class OverleafSession(CommonBase):
    """
    Represents an Overleaf session.
    """

    cookies: dict[str, str] = Field(
        description='Session cookies keyed by cookie name.'
    )
    csrf_token: str = Field(
        description='CSRF token bound to the session.'
    )
    email: str = Field(
        description='Overleaf account email the session belongs to.'
    )
    created_at: datetime = Field(
        description='Timestamp the session was established at.'
    )

    @property
    def cookie_header(self) -> str:
        return "; ".join(f"{name}={value}" for name, value in self.cookies.items())

    @property
    def auth_headers(self) -> dict[str, str]:
        return {
            "Cookie": self.cookie_header,
            "X-Csrf-Token": self.csrf_token,
            "Accept": "application/json",
        }
