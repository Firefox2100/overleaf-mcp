from httpx import AsyncClient

from overleaf_mcp.models.history import DiffChunk, HistoryLabel, HistoryPage, RestoredEntity
from overleaf_mcp.models.overleaf_session import OverleafSession


class OverleafHistoryError(Exception):
    """Raised when Overleaf rejects a history operation."""


class OverleafHistoryService:
    def __init__(self,
                 client: AsyncClient
                 ):
        self._client = client

    async def list_updates(
            self,
            session: OverleafSession,
            project_id: str,
            before: int | None = None,
            min_count: int | None = None,
    ) -> HistoryPage:
        """
        List a project's change history, most recent first. Flushes
        pending edits into history first, so recent changes are included.
        :return:
        """
        await self._flush(session, project_id)
        params = {}
        if before is not None:
            params["before"] = before
        if min_count is not None:
            params["min_count"] = min_count
        response = await self._client.get(
            f"/project/{project_id}/updates",
            params=params,
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafHistoryError(f"Listing history failed with status {response.status_code}: {response.text}")
        return HistoryPage.model_validate_json(response.text)

    async def get_diff(
            self,
            session: OverleafSession,
            project_id: str,
            pathname: str,
            from_version: int,
            to_version: int,
    ) -> list[DiffChunk]:
        """
        Get a doc's diff between two history versions. Flushes pending
        edits into history first, so a diff up to the latest version
        reflects them.
        :return:
        """
        await self._flush(session, project_id)
        response = await self._client.get(
            f"/project/{project_id}/diff",
            params={"pathname": pathname, "from": from_version, "to": to_version},
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafHistoryError(f"Getting diff failed with status {response.status_code}: {response.text}")
        return [DiffChunk.model_validate(chunk) for chunk in response.json()["diff"]]

    async def restore_file(
            self,
            session: OverleafSession,
            project_id: str,
            pathname: str,
            version: int,
    ) -> RestoredEntity:
        """
        Restore a file's content as of a past version. Adds it as a new
        entity alongside the current one (named e.g. "main (Restored on
        ...).tex") rather than overwriting in place.
        :return:
        """
        response = await self._client.post(
            f"/project/{project_id}/restore_file",
            json={"_csrf": session.csrf_token, "version": version, "pathname": pathname},
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafHistoryError(f"Restoring file failed with status {response.status_code}: {response.text}")
        return RestoredEntity.model_validate_json(response.text)

    async def list_labels(self, session: OverleafSession, project_id: str) -> list[HistoryLabel]:
        """
        List a project's labeled (named) history versions.
        :return:
        """
        response = await self._client.get(
            f"/project/{project_id}/labels",
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafHistoryError(f"Listing labels failed with status {response.status_code}: {response.text}")
        return [HistoryLabel.model_validate(label) for label in response.json()]

    async def create_label(
            self,
            session: OverleafSession,
            project_id: str,
            comment: str,
            version: int,
    ) -> HistoryLabel:
        """
        Label a history version, e.g. to mark a known-good checkpoint.
        :return:
        """
        response = await self._client.post(
            f"/project/{project_id}/labels",
            json={"_csrf": session.csrf_token, "comment": comment, "version": version},
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafHistoryError(f"Creating label failed with status {response.status_code}: {response.text}")
        return HistoryLabel.model_validate_json(response.text)

    async def _flush(self, session: OverleafSession, project_id: str) -> None:
        response = await self._client.post(
            f"/project/{project_id}/flush",
            headers=session.auth_headers,
        )
        if response.status_code not in (200, 204):
            raise OverleafHistoryError(f"Flushing history failed with status {response.status_code}: {response.text}")
