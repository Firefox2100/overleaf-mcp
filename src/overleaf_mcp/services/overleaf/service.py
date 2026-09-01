from httpx import AsyncClient

from .auth import OverleafAuthService
from .project import OverleafProjectService


class OverleafService:
    def __init__(self,
                 client: AsyncClient
                 ):
        self._client = client

        self._auth = OverleafAuthService(self._client)
        self._project = OverleafProjectService(self._client)

    @property
    def auth(self) -> OverleafAuthService:
        return self._auth

    @property
    def project(self) -> OverleafProjectService:
        return self._project
