from httpx import AsyncClient

from overleaf_mcp.models.github_sync import GitHubSyncState
from overleaf_mcp.models.overleaf_session import OverleafSession


class OverleafGitHubSyncError(Exception):
    """Raised when Overleaf rejects a GitHub-sync operation (CEP)."""


class OverleafGitHubSyncService:
    def __init__(self,
                 client: AsyncClient
                 ):
        self._client = client

    async def get_state(self, session: OverleafSession, project_id: str) -> GitHubSyncState:
        """
        Get a project's GitHub-sync link state.
        :return:
        """
        response = await self._client.get(
            f"/project/{project_id}/github-sync/state",
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafGitHubSyncError(f"Getting sync state failed with status {response.status_code}: {response.text}")
        return GitHubSyncState.model_validate_json(response.text)

    async def trigger_sync(
            self,
            session: OverleafSession,
            project_id: str,
            message: str = "Updates from Overleaf",
    ) -> dict:
        """
        Sync an already-linked project with its GitHub repo: pulls
        upstream commits, merges them in, then pushes. Fails if the
        project isn't linked (check get_state first). The merge result's
        exact shape isn't pinned down (unverified against a live server
        with this feature enabled), so it's returned as-is.
        :return:
        """
        response = await self._client.post(
            f"/project/{project_id}/github-sync/merge",
            json={"_csrf": session.csrf_token, "message": message},
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafGitHubSyncError(f"Sync failed with status {response.status_code}: {response.text}")
        return response.json()
