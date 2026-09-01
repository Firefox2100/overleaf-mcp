import asyncio
import re

import bibtexparser

from overleaf_mcp.models.citation import CitationCheckResult, CitationEntry
from overleaf_mcp.models.editing import SearchMatch
from overleaf_mcp.models.overleaf_session import OverleafSession
from overleaf_mcp.models.project_tree import flatten_docs
from overleaf_mcp.services.overleaf.file import OverleafFileService
from overleaf_mcp.services.overleaf.realtime import OverleafRealtimeService

# Matches \cite, \citep, \citet, \citeauthor, \citeyear(par), \parencite,
# \textcite, \footcite, \autocite, \fullcite, \nocite, and starred/optional-
# arg variants — anything containing "cite" in the command name.
_CITE_PATTERN = re.compile(r"\\[A-Za-z]*[Cc]ite[A-Za-z]*\*?(?:\[[^\]]*\])*\{(?P<keys>[^}]*)\}")


class CitationError(Exception):
    """Raised when a citation lookup doesn't resolve as expected."""


class CitationComponent:
    def __init__(self,
                 file_service: OverleafFileService,
                 realtime_service: OverleafRealtimeService,
                 ):
        self._file = file_service
        self._realtime = realtime_service

    async def list_citation_files(self, session: OverleafSession, project_id: str) -> list[str]:
        """
        List every .bib file in a project, recursively.
        :return:
        """
        tree = await self._realtime.get_tree(session, project_id)
        return [path for path, _doc_id in flatten_docs(tree) if path.lower().endswith(".bib")]

    async def list_citations(
            self,
            session: OverleafSession,
            project_id: str,
            path: str | None = None,
    ) -> list[CitationEntry]:
        """
        List BibTeX entries. Reads every .bib file in the project, or just
        `path` if given.
        :return:
        """
        tree = await self._realtime.get_tree(session, project_id)
        docs = flatten_docs(tree)
        if path is not None:
            doc_id = next((doc_id for doc_path, doc_id in docs if doc_path == path), None)
            if doc_id is None:
                raise CitationError(f"No such path: {path!r}")
            targets = [(path, doc_id)]
        else:
            targets = [(doc_path, doc_id) for doc_path, doc_id in docs if doc_path.lower().endswith(".bib")]

        contents = await asyncio.gather(*(self._file.read_doc(session, project_id, doc_id) for _, doc_id in targets))
        entries = []
        for (doc_path, _doc_id), content in zip(targets, contents):
            entries += _parse_bib(content, doc_path)
        return entries

    async def find_citation(self, session: OverleafSession, project_id: str, key: str) -> CitationEntry:
        """
        Find a BibTeX entry by its citation key.
        :return:
        """
        for entry in await self.list_citations(session, project_id):
            if entry.key == key:
                return entry
        raise CitationError(f"No citation found for key {key!r}")

    async def find_citation_usage(self, session: OverleafSession, project_id: str, key: str) -> list[SearchMatch]:
        """
        Find every \\cite-family command referencing a citation key.
        :return:
        """
        docs, contents = await self._read_all_docs(session, project_id)
        matches = []
        for path, content in zip((path for path, _id in docs), contents):
            for line_number, line in enumerate(content.split("\n"), start=1):
                if any(key in _split_keys(match.group("keys")) for match in _CITE_PATTERN.finditer(line)):
                    matches.append(SearchMatch(path=path, line=line_number, text=line))
        return matches

    async def check_citations(self, session: OverleafSession, project_id: str) -> CitationCheckResult:
        """
        Cross-reference citation usage against BibTeX definitions across
        the whole project: keys used but never defined, and keys defined
        but never used.
        :return:
        """
        docs, contents = await self._read_all_docs(session, project_id)

        defined_keys: set[str] = set()
        used_keys: set[str] = set()
        for (path, _doc_id), content in zip(docs, contents):
            if path.lower().endswith(".bib"):
                defined_keys.update(entry.key for entry in _parse_bib(content, path))
            else:
                for match in _CITE_PATTERN.finditer(content):
                    used_keys.update(_split_keys(match.group("keys")))

        return CitationCheckResult(
            undefined_keys=sorted(used_keys - defined_keys),
            unused_keys=sorted(defined_keys - used_keys),
        )

    async def _read_all_docs(
            self,
            session: OverleafSession,
            project_id: str,
    ) -> tuple[list[tuple[str, str]], list[str]]:
        tree = await self._realtime.get_tree(session, project_id)
        docs = flatten_docs(tree)
        contents = await asyncio.gather(*(self._file.read_doc(session, project_id, doc_id) for _, doc_id in docs))
        return docs, contents


def _split_keys(raw_keys: str) -> list[str]:
    return [key.strip() for key in raw_keys.split(",") if key.strip()]


def _parse_bib(content: str, path: str) -> list[CitationEntry]:
    database = bibtexparser.loads(content)
    return [
        CitationEntry(
            key=raw["ID"],
            entry_type=raw["ENTRYTYPE"],
            path=path,
            fields={k: v for k, v in raw.items() if k not in ("ID", "ENTRYTYPE")},
        )
        for raw in database.entries
    ]
