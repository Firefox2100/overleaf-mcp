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
            + [
                FileEntry(name=f.name, type="file", linked_file_data=f.linked_file_data)
                for f in folder.file_refs
            ]
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

    async def move_file(self, session: OverleafSession, project_id: str, path: str, destination_folder: str) -> None:
        """
        Move a doc or file into a different folder, keeping its name.
        :return:
        """
        tree = await self._realtime.get_tree(session, project_id)
        entity_type, entity_id = resolve_entity(tree, path)
        if entity_type == "folder":
            raise FilesError(f"{path!r} is a folder")
        target = resolve_folder(tree, destination_folder)
        await self._file.move_entity(session, project_id, entity_type, entity_id, target.id)

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

    async def create_linked_url_file(self, session: OverleafSession, project_id: str, path: str, url: str) -> None:
        """
        Create a file fetched from, and refreshable from, an external URL.
        The parent folder must already exist.
        :return:
        """
        tree = await self._realtime.get_tree(session, project_id)
        parent_path, name = _split_path(path)
        parent = resolve_folder(tree, parent_path)
        if _find_child(parent, name) is not None:
            raise FilesError(f"{path!r} already exists")
        await self._file.create_linked_file(session, project_id, name, "url", {"url": url}, parent.id)

    async def refresh_linked_file(self, session: OverleafSession, project_id: str, path: str) -> None:
        """
        Re-fetch a linked file's content from its source (a URL, or
        Zotero if it was linked via the web UI — this bridge doesn't do
        the Zotero OAuth/linking itself, only triggers a re-sync of an
        already-linked file).
        :return:
        """
        tree = await self._realtime.get_tree(session, project_id)
        entity_type, entity_id = resolve_entity(tree, path)
        if entity_type != "file":
            raise FilesError(f"{path!r} is not a linked file")
        await self._file.refresh_linked_file(session, project_id, entity_id)

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
