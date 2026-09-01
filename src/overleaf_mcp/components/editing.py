import asyncio
import re

from overleaf_mcp.models.editing import OutlineEntry, SearchMatch
from overleaf_mcp.models.overleaf_session import OverleafSession
from overleaf_mcp.models.project_tree import TreeFolder
from overleaf_mcp.services.overleaf.file import OverleafFileService
from overleaf_mcp.services.overleaf.realtime import OverleafRealtimeService

from .files import FilesComponent

_SECTION_LEVELS = ["part", "chapter", "section", "subsection", "subsubsection", "paragraph", "subparagraph"]
_SECTION_PATTERN = re.compile(
    r"^[ \t]*\\(" + "|".join(_SECTION_LEVELS) + r")\*?\{(?P<title>[^}]*)\}",
    re.MULTILINE,
)


class EditingError(Exception):
    """Raised when an editing/navigation operation's arguments don't resolve."""


class EditingComponent:
    def __init__(self,
                 files_component: FilesComponent,
                 file_service: OverleafFileService,
                 realtime_service: OverleafRealtimeService,
                 ):
        self._files = files_component
        self._file = file_service
        self._realtime = realtime_service

    async def search_project(
            self,
            session: OverleafSession,
            project_id: str,
            query: str,
            regex: bool = False,
    ) -> list[SearchMatch]:
        """
        Search every text document in a project for a plain substring or
        regex pattern. Overleaf has no server-side search API for this —
        its own editor searches client-side over content it already has;
        this fetches every document itself instead, so it's O(doc count)
        requests.
        :return:
        """
        tree = await self._realtime.get_tree(session, project_id)
        docs = _flatten_docs(tree)
        contents = await asyncio.gather(*(self._file.read_doc(session, project_id, doc_id) for _, doc_id in docs))

        pattern = re.compile(query) if regex else None
        matches: list[SearchMatch] = []
        for (path, _doc_id), content in zip(docs, contents):
            matches.extend(_search_text(path, content, query, pattern))
        return matches

    async def search_file(
            self,
            session: OverleafSession,
            project_id: str,
            path: str,
            query: str,
            regex: bool = False,
    ) -> list[SearchMatch]:
        """
        Search a single text document for a plain substring or regex pattern.
        :return:
        """
        content = await self._files.read_file(session, project_id, path)
        pattern = re.compile(query) if regex else None
        return _search_text(path, content, query, pattern)

    async def get_outline(self, session: OverleafSession, project_id: str, path: str) -> list[OutlineEntry]:
        """
        Get a document's section/subsection outline by matching LaTeX
        sectioning commands. This is a regex-based approximation of
        Overleaf's own client-side outline parser (a full LaTeX grammar) —
        it doesn't filter out sectioning commands inside \\newcommand
        definitions, unwrap \\texorpdfstring, or include beamer frames.
        :return:
        """
        content = await self._files.read_file(session, project_id, path)
        return _build_outline(content)

    async def read_lines(
            self,
            session: OverleafSession,
            project_id: str,
            path: str,
            start_line: int,
            end_line: int,
    ) -> str:
        """
        Read a range of lines (1-indexed, inclusive) from a text document,
        cat -n style, so a large document doesn't need to be read in full.
        :return:
        """
        if start_line < 1 or start_line > end_line:
            raise EditingError(f"Invalid line range: {start_line}-{end_line}")

        content = await self._files.read_file(session, project_id, path)
        lines = content.split("\n")
        selected = lines[start_line - 1:end_line]
        width = len(str(min(end_line, len(lines))))
        return "\n".join(f"{start_line + i:>{width}}\t{line}" for i, line in enumerate(selected))


def _flatten_docs(folder: TreeFolder, prefix: str = "") -> list[tuple[str, str]]:
    docs = [(f"{prefix}/{doc.name}" if prefix else doc.name, doc.id) for doc in folder.docs]
    for child in folder.folders:
        child_prefix = f"{prefix}/{child.name}" if prefix else child.name
        docs += _flatten_docs(child, child_prefix)
    return docs


def _search_text(path: str, content: str, query: str, pattern: re.Pattern | None) -> list[SearchMatch]:
    matches = []
    for i, line in enumerate(content.split("\n"), start=1):
        hit = pattern.search(line) if pattern else query in line
        if hit:
            matches.append(SearchMatch(path=path, line=i, text=line))
    return matches


def _build_outline(content: str) -> list[OutlineEntry]:
    root: list[OutlineEntry] = []
    stack: list[tuple[int, OutlineEntry]] = []
    for match in _SECTION_PATTERN.finditer(content):
        level_index = _SECTION_LEVELS.index(match.group(1))
        entry = OutlineEntry(
            level=_SECTION_LEVELS[level_index],
            title=match.group("title").strip(),
            line=content.count("\n", 0, match.start()) + 1,
        )
        while stack and stack[-1][0] >= level_index:
            stack.pop()
        (stack[-1][1].children if stack else root).append(entry)
        stack.append((level_index, entry))
    return root
