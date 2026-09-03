import secrets

from overleaf_mcp.models.overleaf_session import OverleafSession
from overleaf_mcp.models.project_tree import TreeFolder, path_segments, resolve_folder
from overleaf_mcp.services.overleaf.file import OverleafFileService
from overleaf_mcp.services.overleaf.pandoc import OverleafPandocService, PandocFormat
from overleaf_mcp.services.overleaf.project import OverleafProjectService
from overleaf_mcp.services.overleaf.realtime import OverleafRealtimeService

# Overleaf's own plain-text extension list (ol-ExposedSettings' textExtensions,
# observed live) — anything else is treated as binary.
_TEXT_EXTENSIONS = {
    "tex", "latex", "sty", "cls", "bst", "bib", "bibtex", "txt", "tikz", "mtx", "rtex",
    "md", "asy", "lbx", "bbx", "cbx", "m", "lco", "dtx", "ins", "ist", "def", "clo",
    "ldf", "rmd", "qmd", "lua", "py", "gv", "mf", "yml", "yaml", "lhs", "lean", "lean4",
    "hs", "mk", "xmpdata", "cfg", "rnw", "ltx", "inc",
}
_PANDOC_EXTENSIONS = {"docx": "docx", "md": "markdown", "markdown": "markdown"}


class PandocError(Exception):
    """Raised when a Pandoc (CEP) operation's arguments don't resolve, or fails."""


class PandocComponent:
    def __init__(self,
                 project_service: OverleafProjectService,
                 file_service: OverleafFileService,
                 realtime_service: OverleafRealtimeService,
                 pandoc_service: OverleafPandocService,
                 ):
        self._project = project_service
        self._file = file_service
        self._realtime = realtime_service
        self._pandoc = pandoc_service

    async def export_project(self, session: OverleafSession, project_id: str, format: PandocFormat) -> bytes:
        """
        Convert the whole project to docx, markdown, or html.
        :return:
        """
        return await self._pandoc.export_project(session, project_id, format)

    async def import_file(
            self,
            session: OverleafSession,
            project_id: str,
            destination_folder: str,
            filename: str,
            content: bytes,
    ) -> list[str]:
        """
        Add a file to destination_folder (which must already exist),
        converting it first if it's a document Overleaf can't use
        directly (.docx, .md) — landing as one or more files there
        (whatever the conversion produces, e.g. a .tex file plus any
        extracted images), named after filename otherwise. Returns the
        paths of everything created.
        :return:
        """
        extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        path = f"{destination_folder}/{filename}" if destination_folder else filename

        if extension in _TEXT_EXTENSIONS:
            await self._create_plain_file(session, project_id, path, content.decode("utf-8"))
            return [path]
        if extension not in _PANDOC_EXTENSIONS:
            await self._upload_binary_file(session, project_id, path, content)
            return [path]

        temp_project_id = await self._pandoc.import_document(
            session, f"pandoc-import-{secrets.token_hex(8)}", _PANDOC_EXTENSIONS[extension], filename, content,
        )
        try:
            source_tree = await self._realtime.get_tree(session, temp_project_id)
            target_tree = await self._realtime.get_tree(session, project_id)
            destination = resolve_folder(target_tree, destination_folder)
            created: list[str] = []
            await self._copy_tree(
                session, project_id, destination.id, temp_project_id, source_tree, destination_folder, created,
            )
            return created
        finally:
            await self._project.delete_project(session, temp_project_id)

    async def _create_plain_file(self, session: OverleafSession, project_id: str, path: str, content: str) -> None:
        tree = await self._realtime.get_tree(session, project_id)
        segments = path_segments(path)
        parent = resolve_folder(tree, "/".join(segments[:-1]))
        created = await self._file.create_doc(session, project_id, segments[-1], parent.id)
        if content:
            await self._realtime.replace_doc(session, project_id, created.id, content)

    async def _upload_binary_file(self, session: OverleafSession, project_id: str, path: str, content: bytes) -> None:
        tree = await self._realtime.get_tree(session, project_id)
        segments = path_segments(path)
        parent = resolve_folder(tree, "/".join(segments[:-1]))
        await self._file.upload_file(session, project_id, parent.id, segments[-1], content)

    async def _copy_tree(
            self,
            session: OverleafSession,
            target_project_id: str,
            target_folder_id: str,
            source_project_id: str,
            source_folder: TreeFolder,
            dest_prefix: str,
            created: list[str],
    ) -> None:
        for doc in source_folder.docs:
            content = await self._file.read_doc(session, source_project_id, doc.id)
            new_doc = await self._file.create_doc(session, target_project_id, doc.name, target_folder_id)
            if content:
                await self._realtime.replace_doc(session, target_project_id, new_doc.id, content)
            created.append(f"{dest_prefix}/{doc.name}" if dest_prefix else doc.name)

        for file_ref in source_folder.file_refs:
            content = await self._file.read_file(session, source_project_id, file_ref.id)
            await self._file.upload_file(session, target_project_id, target_folder_id, file_ref.name, content)
            created.append(f"{dest_prefix}/{file_ref.name}" if dest_prefix else file_ref.name)

        for sub_folder in source_folder.folders:
            new_folder = await self._file.create_folder(session, target_project_id, sub_folder.name, target_folder_id)
            sub_prefix = f"{dest_prefix}/{sub_folder.name}" if dest_prefix else sub_folder.name
            await self._copy_tree(session, target_project_id, new_folder.id, source_project_id, sub_folder, sub_prefix, created)
