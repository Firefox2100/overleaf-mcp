import secrets

from overleaf_mcp.models.comment import CommentThread
from overleaf_mcp.models.overleaf_session import OverleafSession
from overleaf_mcp.models.project_tree import flatten_docs, resolve_entity
from overleaf_mcp.services.overleaf.file import OverleafFileService
from overleaf_mcp.services.overleaf.realtime import OverleafRealtimeService
from overleaf_mcp.services.overleaf.review import OverleafReviewService


class CommentError(Exception):
    """Raised when a comment operation's arguments don't resolve."""


class CommentComponent:
    def __init__(self,
                 realtime_service: OverleafRealtimeService,
                 review_service: OverleafReviewService,
                 file_service: OverleafFileService,
                 ):
        self._realtime = realtime_service
        self._review = review_service
        self._file = file_service

    async def list_comments(
            self,
            session: OverleafSession,
            project_id: str,
            path: str | None = None,
    ) -> list[CommentThread]:
        """
        List comment threads across the project, or just in one document
        if path is given. Also returns threads whose comment anchor no
        longer exists (e.g. its text was deleted) — those have no path or
        anchor_text.
        :return:
        """
        raw_ranges = await self._review.list_ranges(session, project_id)
        raw_threads = await self._review.list_threads(session, project_id)

        anchors: dict[str, tuple[str, str]] = {}
        for entry in raw_ranges:
            for comment in entry.get("ranges", {}).get("comments", []):
                op = comment["op"]
                anchors[op["t"]] = (entry["id"], op.get("c", ""))

        tree = await self._realtime.get_tree(session, project_id)
        path_by_doc_id = {doc_id: doc_path for doc_path, doc_id in flatten_docs(tree)}

        threads = []
        for thread_id, thread in raw_threads.items():
            doc_id, anchor_text = anchors.get(thread_id, (None, None))
            doc_path = path_by_doc_id.get(doc_id) if doc_id else None
            if path is not None and doc_path != path:
                continue
            threads.append(CommentThread.model_validate({
                **thread,
                "id": thread_id,
                "path": doc_path,
                "anchor_text": anchor_text,
            }))
        return threads

    async def create_comment(
            self,
            session: OverleafSession,
            project_id: str,
            path: str,
            find: str,
            content: str,
    ) -> str:
        """
        Anchor a new comment thread to the single occurrence of `find` in a
        document and post its first message. Returns the new thread id.
        :return:
        """
        doc_id = await self._resolve_doc(session, project_id, path)
        doc_text = await self._file.read_doc(session, project_id, doc_id)

        count = doc_text.count(find)
        if count == 0:
            raise CommentError(f"No match for {find!r} in {path!r}")
        if count > 1:
            raise CommentError(f"{find!r} is not unique in {path!r} ({count} matches)")
        position = doc_text.index(find)

        thread_id = secrets.token_hex(12)
        await self._review.post_message(session, project_id, thread_id, content)
        await self._realtime.add_comment(session, project_id, doc_id, position, find, thread_id)
        return thread_id

    async def reply_comment(self, session: OverleafSession, project_id: str, thread_id: str, content: str) -> None:
        """
        Reply to an existing comment thread.
        :return:
        """
        await self._review.post_message(session, project_id, thread_id, content)

    async def resolve_comment(self, session: OverleafSession, project_id: str, path: str, thread_id: str) -> None:
        """
        Mark a comment thread resolved.
        :return:
        """
        doc_id = await self._resolve_doc(session, project_id, path)
        await self._review.resolve_thread(session, project_id, doc_id, thread_id)

    async def reopen_comment(self, session: OverleafSession, project_id: str, path: str, thread_id: str) -> None:
        """
        Reopen a resolved comment thread.
        :return:
        """
        doc_id = await self._resolve_doc(session, project_id, path)
        await self._review.reopen_thread(session, project_id, doc_id, thread_id)

    async def delete_comment(self, session: OverleafSession, project_id: str, path: str, thread_id: str) -> None:
        """
        Delete a comment thread entirely.
        :return:
        """
        doc_id = await self._resolve_doc(session, project_id, path)
        await self._review.delete_thread(session, project_id, doc_id, thread_id)

    async def _resolve_doc(self, session: OverleafSession, project_id: str, path: str) -> str:
        tree = await self._realtime.get_tree(session, project_id)
        entity_type, entity_id = resolve_entity(tree, path)
        if entity_type != "doc":
            raise CommentError(f"{path!r} is not a text document")
        return entity_id
