import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from overleaf_mcp.components.citation import CitationComponent, CitationError, _parse_bib, _split_keys
from overleaf_mcp.models.project_tree import TreeEntity, TreeFolder


class CitationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tree = TreeFolder(
            id="root",
            name="root",
            docs=[TreeEntity(id="main", name="main.tex")],
            file_refs=[TreeEntity(id="refs", name="references.bib", linked_file_data={"provider": "zotero"})],
        )
        self.file = SimpleNamespace(
            read_doc=AsyncMock(return_value="See \\citep[pp. 1--2]{defined, missing}."),
            read_file=AsyncMock(return_value=b"@article{defined, title={Used}}\n@book{unused, title={Unused}}"),
        )
        self.realtime = SimpleNamespace(get_tree=AsyncMock(return_value=tree))
        self.component = CitationComponent(self.file, self.realtime)

    async def test_lists_and_parses_linked_bibliographies(self):
        self.assertEqual(await self.component.list_citation_files(None, "p"), ["references.bib"])
        entries = await self.component.list_citations(None, "p")
        self.assertEqual([(entry.key, entry.entry_type, entry.path) for entry in entries], [
            ("defined", "article", "references.bib"),
            ("unused", "book", "references.bib"),
        ])
        self.assertEqual((await self.component.find_citation(None, "p", "defined")).fields["title"], "Used")

    async def test_finds_usage_and_reports_undefined_and_unused_keys(self):
        matches = await self.component.find_citation_usage(None, "p", "missing")
        self.assertEqual([(match.path, match.line) for match in matches], [("main.tex", 1)])
        result = await self.component.check_citations(None, "p")
        self.assertEqual(result.undefined_keys, ["missing"])
        self.assertEqual(result.unused_keys, ["unused"])

    async def test_rejects_unknown_paths_and_keys(self):
        with self.assertRaisesRegex(CitationError, "No such path"):
            await self.component.list_citations(None, "p", "missing.bib")
        with self.assertRaisesRegex(CitationError, "No citation found"):
            await self.component.find_citation(None, "p", "missing")

    def test_helpers_parse_bibtex_and_keys(self):
        self.assertEqual(_split_keys(" first, ,second "), ["first", "second"])
        entry = _parse_bib("@misc{key, note={value}}", "refs.bib")[0]
        self.assertEqual((entry.key, entry.fields), ("key", {"note": "value"}))


if __name__ == "__main__":
    unittest.main()
