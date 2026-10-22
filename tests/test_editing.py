import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from overleaf_mcp.components.editing import EditingComponent, EditingError
from overleaf_mcp.models.entity import FileContent
from overleaf_mcp.models.project_tree import TreeEntity, TreeFolder


class EditingComponentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        tree = TreeFolder(
            id="root",
            name="root",
            docs=[TreeEntity(id="main", name="main.tex")],
            file_refs=[
                TreeEntity(id="refs", name="refs.bib"),
                TreeEntity(id="image", name="figure.png"),
            ],
        )
        self.files = SimpleNamespace(
            read_file=AsyncMock(
                return_value=FileContent(
                    content="\\section{Introduction}\nfirst needle\n\\subsection*{Details}\nsecond needle",
                    type="doc",
                )
            )
        )

        async def read_doc(_session, _project_id, _entity_id):
            return "needle in document"

        async def read_file(_session, _project_id, entity_id):
            return b"needle in bibliography" if entity_id == "refs" else b"\xff\xfe"

        self.file_service = SimpleNamespace(read_doc=read_doc, read_file=read_file)
        self.realtime = SimpleNamespace(get_tree=AsyncMock(return_value=tree))
        self.component = EditingComponent(self.files, self.file_service, self.realtime)

    async def test_searches_documents_and_text_files_but_skips_binary_files(self):
        matches = await self.component.search_project(None, "p", r"needle", regex=True)
        self.assertEqual(
            [(match.path, match.line) for match in matches],
            [("main.tex", 1), ("refs.bib", 1)],
        )

    async def test_searches_one_file_and_builds_nested_outline(self):
        matches = await self.component.search_file(None, "p", "main.tex", "needle")
        self.assertEqual([match.line for match in matches], [2, 4])

        outline = await self.component.get_outline(None, "p", "main.tex")
        self.assertEqual((outline[0].level, outline[0].title, outline[0].line), ("section", "Introduction", 1))
        self.assertEqual((outline[0].children[0].level, outline[0].children[0].title), ("subsection", "Details"))

    async def test_reads_numbered_ranges_and_validates_them(self):
        self.assertEqual(
            await self.component.read_lines(None, "p", "main.tex", 2, 3),
            "2\tfirst needle\n3\t\\subsection*{Details}",
        )
        with self.assertRaisesRegex(EditingError, "Invalid line range"):
            await self.component.read_lines(None, "p", "main.tex", 3, 2)


if __name__ == "__main__":
    unittest.main()
