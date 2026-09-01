from overleaf_mcp.models.overleaf_session import OverleafSession
from overleaf_mcp.models.project_config import ProjectConfig
from overleaf_mcp.models.project_tree import TreeFolder, find_doc_path

from .socket_io import SocketIOClient


class OverleafRealtimeError(Exception):
    """
    Raised when Overleaf's real-time API rejects an operation, or when a
    post-write consistency check fails.
    """


class OverleafRealtimeService:
    def __init__(self,
                 base_url: str
                 ):
        self._base_url = base_url

    async def get_tree(self, session: OverleafSession, project_id: str) -> TreeFolder:
        """
        Fetch the project's live folder tree (with entity ids), by joining
        the project over the real-time API. Not cached: this process is
        short-lived (spawned per LLM turn), and without a held-open socket
        there's no way to detect staleness, so every caller re-fetches.
        :return:
        """
        raw = await self._join_project(session, project_id)
        return TreeFolder.model_validate(raw["rootFolder"][0])

    async def get_project_info(self, session: OverleafSession, project_id: str) -> ProjectConfig:
        """
        Fetch a project's compile-relevant configuration (compiler, root
        document, spell-check language, TeX Live image) plus resolved
        paths for the root and bibliography documents, by joining the
        project over the real-time API. CE has no plain REST endpoint for
        this.
        :return:
        """
        raw = await self._join_project(session, project_id)
        config = ProjectConfig.model_validate(raw)
        tree = TreeFolder.model_validate(raw["rootFolder"][0])
        return config.model_copy(update={
            "root_doc_path": find_doc_path(tree, config.root_doc_id) if config.root_doc_id else None,
            "main_bibliography_doc_path": (
                find_doc_path(tree, config.main_bibliography_doc_id) if config.main_bibliography_doc_id else None
            ),
        })

    async def _join_project(self, session: OverleafSession, project_id: str) -> dict:
        async with SocketIOClient(self._base_url, session.cookie_header, {"projectId": project_id}) as sio:
            reply = await sio.call("joinProject", [{"project_id": project_id}])
            return reply.args[0]["project"]

    async def replace_doc(self, session: OverleafSession, project_id: str, doc_id: str, new_text: str) -> None:
        """
        Replace a doc's entire content.
        :return:
        """
        async with SocketIOClient(self._base_url, session.cookie_header, {"projectId": project_id}) as sio:
            await sio.call("joinProject", [{"project_id": project_id}])
            lines, version = await self._join_doc(sio, doc_id)
            old_text = "\n".join(lines)
            if old_text != new_text:
                await self._apply_and_verify(sio, doc_id, _full_replace_op(old_text, new_text), version, new_text)
            await self._leave_doc(sio, doc_id)

    async def patch_doc(self, session: OverleafSession, project_id: str, doc_id: str, find: str, replace: str) -> None:
        """
        Replace the single occurrence of `find` in a doc with `replace`.
        Raises if `find` doesn't occur exactly once.
        :return:
        """
        async with SocketIOClient(self._base_url, session.cookie_header, {"projectId": project_id}) as sio:
            await sio.call("joinProject", [{"project_id": project_id}])
            lines, version = await self._join_doc(sio, doc_id)
            old_text = "\n".join(lines)

            count = old_text.count(find)
            if count == 0:
                await self._leave_doc(sio, doc_id)
                raise OverleafRealtimeError(f"No match for {find!r} in the document")
            if count > 1:
                await self._leave_doc(sio, doc_id)
                raise OverleafRealtimeError(f"{find!r} is not unique in the document ({count} matches)")

            index = old_text.index(find)
            new_text = old_text[:index] + replace + old_text[index + len(find):]
            op = ([{"p": index, "d": find}] if find else []) + ([{"p": index, "i": replace}] if replace else [])
            await self._apply_and_verify(sio, doc_id, op, version, new_text)
            await self._leave_doc(sio, doc_id)

    async def _join_doc(self, sio: SocketIOClient, doc_id: str) -> tuple[list[str], int]:
        error, lines, version, *_rest = await sio.emit_with_ack("joinDoc", [doc_id, -1, {}])
        if error:
            raise OverleafRealtimeError(f"joinDoc failed: {error}")
        return lines, version

    async def _leave_doc(self, sio: SocketIOClient, doc_id: str) -> None:
        await sio.emit("leaveDoc", [doc_id])

    async def _apply_and_verify(
            self,
            sio: SocketIOClient,
            doc_id: str,
            op: list[dict],
            version: int,
            expected_text: str,
    ) -> None:
        if not op:
            return
        ack = await sio.emit_with_ack("applyOtUpdate", [doc_id, {"doc": doc_id, "op": op, "v": version}])
        if ack:
            raise OverleafRealtimeError(f"applyOtUpdate failed: {ack}")

        # Overleaf's OT transforms stale updates instead of rejecting them,
        # and silently drops a delete op whose payload doesn't match the
        # current text — so a concurrent edit wouldn't surface as an error
        # here. Re-read and confirm the result is what we intended.
        lines, _version = await self._join_doc(sio, doc_id)
        if "\n".join(lines) != expected_text:
            raise OverleafRealtimeError(
                "Post-write verification failed: the document's content doesn't match what "
                "was written, likely due to a concurrent edit"
            )


def _full_replace_op(old_text: str, new_text: str) -> list[dict]:
    op = []
    if old_text:
        op.append({"p": 0, "d": old_text})
    if new_text:
        op.append({"p": 0, "i": new_text})
    return op
