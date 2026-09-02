from overleaf_mcp.models.overleaf_session import OverleafSession
from overleaf_mcp.models.project_tree import flatten_docs, resolve_entity
from overleaf_mcp.models.tracked_change import TrackedChange
from overleaf_mcp.services.overleaf.realtime import OverleafRealtimeService
from overleaf_mcp.services.overleaf.review import OverleafReviewService


class ReviewError(Exception):
    """Raised when a review-mode operation's arguments don't resolve."""


class ReviewComponent:
    def __init__(self,
                 realtime_service: OverleafRealtimeService,
                 review_service: OverleafReviewService,
                 ):
        self._realtime = realtime_service
        self._review = review_service

    async def set_track_changes(self, session: OverleafSession, project_id: str, enabled: bool) -> None:
        """
        Turn track changes (review mode) on or off for everyone on the
        project.
        :return:
        """
        await self._review.set_track_changes(session, project_id, enabled)

    async def overwrite_file_tracked(self, session: OverleafSession, project_id: str, path: str, content: str) -> None:
        """
        Replace a text document's entire content as a tracked change.
        :return:
        """
        doc_id = await self._resolve_doc(session, project_id, path)
        await self._realtime.replace_doc(session, project_id, doc_id, content, track_changes=True)

    async def patch_file_tracked(
            self,
            session: OverleafSession,
            project_id: str,
            path: str,
            find: str,
            replace: str,
    ) -> None:
        """
        Replace the single occurrence of `find` in a text document with
        `replace`, as a tracked change.
        :return:
        """
        doc_id = await self._resolve_doc(session, project_id, path)
        await self._realtime.patch_doc(session, project_id, doc_id, find, replace, track_changes=True)

    async def list_tracked_changes(
            self,
            session: OverleafSession,
            project_id: str,
            path: str | None = None,
    ) -> list[TrackedChange]:
        """
        List pending tracked changes across the project, or just in one
        document if path is given.
        :return:
        """
        tree = await self._realtime.get_tree(session, project_id)
        path_by_doc_id = {doc_id: doc_path for doc_path, doc_id in flatten_docs(tree)}

        raw = await self._review.list_ranges(session, project_id)
        changes: list[TrackedChange] = []
        for entry in raw:
            doc_path = path_by_doc_id.get(entry["id"])
            if doc_path is None or (path is not None and doc_path != path):
                continue
            for change in entry.get("ranges", {}).get("changes", []):
                op = change["op"]
                changes.append(TrackedChange(
                    id=change["id"],
                    path=doc_path,
                    type="insert" if "i" in op else "delete",
                    text=op.get("i", op.get("d", "")),
                    position=op["p"],
                    user_id=change["metadata"]["user_id"],
                    timestamp=change["metadata"]["ts"],
                ))
        return changes

    async def accept_tracked_changes(
            self,
            session: OverleafSession,
            project_id: str,
            path: str,
            change_ids: list[str],
    ) -> None:
        """
        Accept a document's tracked changes, applying them permanently.
        :return:
        """
        doc_id = await self._resolve_doc(session, project_id, path)
        await self._review.accept_changes(session, project_id, doc_id, change_ids)

    async def reject_tracked_changes(
            self,
            session: OverleafSession,
            project_id: str,
            path: str,
            change_ids: list[str],
    ) -> None:
        """
        Reject a document's tracked changes, undoing them. There is no
        native reject endpoint (Overleaf's own web UI constructs the
        inverse edit and submits it flagged as an undo); applies in
        descending-position order, required for correctness with more
        than one change.
        :return:
        """
        doc_id = await self._resolve_doc(session, project_id, path)
        changes = await self.list_tracked_changes(session, project_id, path)
        by_id = {change.id: change for change in changes}

        missing = [change_id for change_id in change_ids if change_id not in by_id]
        if missing:
            raise ReviewError(f"No tracked change(s) {missing} in {path!r}")

        targets = sorted((by_id[change_id] for change_id in change_ids), key=lambda c: c.position, reverse=True)
        for change in targets:
            await self._realtime.reject_change(
                session, project_id, doc_id, change.position, change.text, change.type == "insert",
            )

    async def _resolve_doc(self, session: OverleafSession, project_id: str, path: str) -> str:
        tree = await self._realtime.get_tree(session, project_id)
        entity_type, entity_id = resolve_entity(tree, path)
        if entity_type != "doc":
            raise ReviewError(f"{path!r} is not a text document")
        return entity_id
