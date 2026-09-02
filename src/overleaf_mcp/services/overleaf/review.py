from httpx import AsyncClient

from overleaf_mcp.models.overleaf_session import OverleafSession


class OverleafReviewError(Exception):
    """Raised when Overleaf rejects a review-mode (CEP) operation."""


class OverleafReviewService:
    def __init__(self,
                 client: AsyncClient
                 ):
        self._client = client

    async def set_track_changes(self, session: OverleafSession, project_id: str, enabled: bool) -> None:
        """
        Turn track changes (review mode) on or off for everyone on the
        project.
        :return:
        """
        response = await self._client.post(
            f"/project/{project_id}/track_changes",
            json={"_csrf": session.csrf_token, "on": enabled},
            headers=session.auth_headers,
        )
        if response.status_code != 204:
            raise OverleafReviewError(f"Setting track changes failed with status {response.status_code}: {response.text}")

    async def list_ranges(self, session: OverleafSession, project_id: str) -> list[dict]:
        """
        Fetch every doc's raw tracked-change/comment ranges in a project.
        :return:
        """
        response = await self._client.get(
            f"/project/{project_id}/ranges",
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafReviewError(f"Listing ranges failed with status {response.status_code}: {response.text}")
        return response.json()

    async def accept_changes(
            self,
            session: OverleafSession,
            project_id: str,
            doc_id: str,
            change_ids: list[str],
    ) -> None:
        """
        Accept a doc's tracked changes, applying them permanently.
        :return:
        """
        response = await self._client.post(
            f"/project/{project_id}/doc/{doc_id}/changes/accept",
            json={"_csrf": session.csrf_token, "change_ids": change_ids},
            headers=session.auth_headers,
        )
        if response.status_code != 204:
            raise OverleafReviewError(f"Accepting changes failed with status {response.status_code}: {response.text}")

    async def list_threads(self, session: OverleafSession, project_id: str) -> dict:
        """
        Fetch every comment thread in a project, keyed by thread id.
        :return:
        """
        response = await self._client.get(
            f"/project/{project_id}/threads",
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafReviewError(f"Listing threads failed with status {response.status_code}: {response.text}")
        return response.json()

    async def post_message(self, session: OverleafSession, project_id: str, thread_id: str, content: str) -> None:
        """
        Post a message into a comment thread, creating the thread first if
        this is its first message. The thread id is client-generated —
        there is no separate "create thread" call.
        :return:
        """
        response = await self._client.post(
            f"/project/{project_id}/thread/{thread_id}/messages",
            json={"_csrf": session.csrf_token, "content": content},
            headers=session.auth_headers,
        )
        if response.status_code != 204:
            raise OverleafReviewError(f"Posting message failed with status {response.status_code}: {response.text}")

    async def resolve_thread(self, session: OverleafSession, project_id: str, doc_id: str, thread_id: str) -> None:
        """
        Mark a comment thread resolved.
        :return:
        """
        response = await self._client.post(
            f"/project/{project_id}/doc/{doc_id}/thread/{thread_id}/resolve",
            json={"_csrf": session.csrf_token},
            headers=session.auth_headers,
        )
        if response.status_code != 204:
            raise OverleafReviewError(f"Resolving thread failed with status {response.status_code}: {response.text}")

    async def reopen_thread(self, session: OverleafSession, project_id: str, doc_id: str, thread_id: str) -> None:
        """
        Reopen a resolved comment thread.
        :return:
        """
        response = await self._client.post(
            f"/project/{project_id}/doc/{doc_id}/thread/{thread_id}/reopen",
            json={"_csrf": session.csrf_token},
            headers=session.auth_headers,
        )
        if response.status_code != 204:
            raise OverleafReviewError(f"Reopening thread failed with status {response.status_code}: {response.text}")

    async def delete_thread(self, session: OverleafSession, project_id: str, doc_id: str, thread_id: str) -> None:
        """
        Delete a comment thread entirely.
        :return:
        """
        response = await self._client.delete(
            f"/project/{project_id}/doc/{doc_id}/thread/{thread_id}",
            headers=session.auth_headers,
        )
        if response.status_code != 204:
            raise OverleafReviewError(f"Deleting thread failed with status {response.status_code}: {response.text}")
