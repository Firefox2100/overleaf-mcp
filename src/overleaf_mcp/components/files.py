from overleaf_mcp.models.entity import EntityType, FileEntry
from overleaf_mcp.models.overleaf_session import OverleafSession
from overleaf_mcp.models.project_tree import TreeFolder, path_segments, resolve_entity, resolve_folder
from overleaf_mcp.services.overleaf.file import OverleafFileService
from overleaf_mcp.services.overleaf.realtime import OverleafRealtimeService


class FilesError(Exception):
    """Raised when a file operation's path doesn't resolve as expected."""


class FilesComponent:
    def __init__(self,
                 file_service: OverleafFileService,
                 realtime_service: OverleafRealtimeService,
                 ):
        self._file = file_service
        self._realtime = realtime_service

    async def list_files(self, session: OverleafSession, project_id: str, path: str = "") -> list[FileEntry]:
        """
        List the immediate contents of a folder.
        :return:
        """
        tree = await self._realtime.get_tree(session, project_id)
        folder = resolve_folder(tree, path)
        return (
            [FileEntry(name=f.name, type="folder") for f in folder.folders]
            + [FileEntry(name=d.name, type="doc") for d in folder.docs]
            + [FileEntry(name=f.name, type="file") for f in folder.file_refs]
        )

    async def read_file(self, session: OverleafSession, project_id: str, path: str) -> str:
        """
        Read a text document's content.
        :return:
        """
        tree = await self._realtime.get_tree(session, project_id)
        entity_type, entity_id = resolve_entity(tree, path)
        _require_doc(path, entity_type)
        return await self._file.read_doc(session, project_id, entity_id)

    async def create_file(self, session: OverleafSession, project_id: str, path: str, content: str = "") -> None:
        """
        Create a new, empty text document at path and optionally set its
        initial content. The parent folder must already exist.
        :return:
        """
        tree = await self._realtime.get_tree(session, project_id)
        parent_path, name = _split_path(path)
        parent = resolve_folder(tree, parent_path)
        if _find_child(parent, name) is not None:
            raise FilesError(f"{path!r} already exists")

        created = await self._file.create_doc(session, project_id, name, parent.id)
        if content:
            await self._realtime.replace_doc(session, project_id, created.id, content)

    async def rename_file(self, session: OverleafSession, project_id: str, path: str, name: str) -> None:
        """
        Rename a doc or file in place.
        :return:
        """
        tree = await self._realtime.get_tree(session, project_id)
        entity_type, entity_id = resolve_entity(tree, path)
        if entity_type == "folder":
            raise FilesError(f"{path!r} is a folder")
        await self._file.rename_entity(session, project_id, entity_type, entity_id, name)

    async def overwrite_file(self, session: OverleafSession, project_id: str, path: str, content: str) -> None:
        """
        Replace a text document's entire content.
        :return:
        """
        tree = await self._realtime.get_tree(session, project_id)
        entity_type, entity_id = resolve_entity(tree, path)
        _require_doc(path, entity_type)
        await self._realtime.replace_doc(session, project_id, entity_id, content)

    async def patch_file(self, session: OverleafSession, project_id: str, path: str, find: str, replace: str) -> None:
        """
        Replace the single occurrence of `find` in a text document with
        `replace`.
        :return:
        """
        tree = await self._realtime.get_tree(session, project_id)
        entity_type, entity_id = resolve_entity(tree, path)
        _require_doc(path, entity_type)
        await self._realtime.patch_doc(session, project_id, entity_id, find, replace)

    async def delete_file(self, session: OverleafSession, project_id: str, path: str) -> None:
        """
        Delete a doc or file.
        :return:
        """
        tree = await self._realtime.get_tree(session, project_id)
        entity_type, entity_id = resolve_entity(tree, path)
        if entity_type == "folder":
            raise FilesError(f"{path!r} is a folder")
        await self._file.delete_entity(session, project_id, entity_type, entity_id)


def _require_doc(path: str, entity_type: EntityType) -> None:
    if entity_type != "doc":
        raise FilesError(f"{path!r} is not a text document")


def _split_path(path: str) -> tuple[str, str]:
    segments = path_segments(path)
    if not segments:
        raise FilesError("Path must not be empty")
    return "/".join(segments[:-1]), segments[-1]


def _find_child(folder: TreeFolder, name: str) -> EntityType | None:
    if any(f.name == name for f in folder.folders):
        return "folder"
    if any(d.name == name for d in folder.docs):
        return "doc"
    if any(f.name == name for f in folder.file_refs):
        return "file"
    return None
