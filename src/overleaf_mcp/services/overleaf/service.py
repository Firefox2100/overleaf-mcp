from httpx import AsyncClient

from .auth import OverleafAuthService
from .compile import OverleafCompileService
from .file import OverleafFileService
from .github_sync import OverleafGitHubSyncService
from .history import OverleafHistoryService
from .pandoc import OverleafPandocService
from .project import OverleafProjectService
from .realtime import OverleafRealtimeService
from .review import OverleafReviewService


class OverleafService:
    def __init__(self,
                 client: AsyncClient
                 ):
        self._client = client

        self._auth = OverleafAuthService(self._client)
        self._project = OverleafProjectService(self._client)
        self._file = OverleafFileService(self._client)
        self._realtime = OverleafRealtimeService(str(self._client.base_url))
        self._compile = OverleafCompileService(self._client)
        self._history = OverleafHistoryService(self._client)
        self._review = OverleafReviewService(self._client)
        self._github_sync = OverleafGitHubSyncService(self._client)
        self._pandoc = OverleafPandocService(self._client)

    @property
    def auth(self) -> OverleafAuthService:
        return self._auth

    @property
    def project(self) -> OverleafProjectService:
        return self._project

    @property
    def file(self) -> OverleafFileService:
        return self._file

    @property
    def realtime(self) -> OverleafRealtimeService:
        return self._realtime

    @property
    def compile(self) -> OverleafCompileService:
        return self._compile

    @property
    def history(self) -> OverleafHistoryService:
        return self._history

    @property
    def review(self) -> OverleafReviewService:
        return self._review

    @property
    def github_sync(self) -> OverleafGitHubSyncService:
        return self._github_sync

    @property
    def pandoc(self) -> OverleafPandocService:
        return self._pandoc
