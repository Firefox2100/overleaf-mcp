import re
from datetime import datetime, timezone

from httpx import AsyncClient

from overleaf_mcp.models.overleaf_session import OverleafSession

_CSRF_META_PATTERN = re.compile(r'name="ol-csrfToken"\s+content="([^"]*)"')


class OverleafAuthError(Exception):
    """Raised when Overleaf rejects a login or logout request."""


class OverleafAuthService:
    def __init__(self,
                 client: AsyncClient
                 ):
        self._client = client

    async def init_session(self, email: str, password: str) -> OverleafSession:
        """
        Initialise an authenticated session with Overleaf.
        :return:
        """
        login_page = await self._client.get("/login", follow_redirects=True)
        login_page.raise_for_status()
        cookies = dict(login_page.cookies)
        csrf_token = self._extract_csrf_token(login_page.text)

        response = await self._client.post(
            "/login",
            json={"email": email, "password": password, "_csrf": csrf_token},
            headers={
                "Cookie": self._serialize_cookies(cookies),
                "X-Csrf-Token": csrf_token,
                "Accept": "application/json",
            },
            follow_redirects=False,
        )
        cookies |= dict(response.cookies)

        if response.status_code != 200:
            raise OverleafAuthError(f"Login failed with status {response.status_code}: {response.text}")

        # Login regenerates the session, invalidating the pre-login CSRF token.
        dashboard = await self._client.get(
            "/project",
            headers={"Cookie": self._serialize_cookies(cookies)},
            follow_redirects=False,
        )
        dashboard.raise_for_status()
        cookies |= dict(dashboard.cookies)
        csrf_token = self._extract_csrf_token(dashboard.text)

        return OverleafSession(
            cookies=cookies,
            csrf_token=csrf_token,
            email=email,
            created_at=datetime.now(timezone.utc),
        )

    async def destroy_session(self, session: OverleafSession) -> None:
        """
        Destroy the authenticated session with Overleaf.
        :return:
        """
        response = await self._client.post(
            "/logout",
            headers=session.auth_headers,
            follow_redirects=False,
        )
        if response.status_code not in (200, 302):
            raise OverleafAuthError(f"Logout failed with status {response.status_code}: {response.text}")

    @staticmethod
    def _extract_csrf_token(html: str) -> str:
        match = _CSRF_META_PATTERN.search(html)
        if not match:
            raise OverleafAuthError("CSRF token not found on login page")
        return match.group(1)

    @staticmethod
    def _serialize_cookies(cookies: dict[str, str]) -> str:
        return "; ".join(f"{name}={value}" for name, value in cookies.items())
