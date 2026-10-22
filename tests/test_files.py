import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from overleaf_mcp.components.files import FilesComponent, FilesError, read_entity_text, try_read_entity_text
from overleaf_mcp.models.project_tree import TreeEntity, TreeFolder


def sample_tree() -> TreeFolder:
    return TreeFolder(
        id="root",
        name="root",
        docs=[TreeEntity(id="main", name="main.tex")],
        file_refs=[
            TreeEntity(id="linked", name="refs.bib", linked_file_data={"provider": "zotero"}),
            TreeEntity(id="image", name="figure.png"),
        ],
        folders=[TreeFolder(id="chapters", name="chapters")],
    )


class EntityTextTests(unittest.IsolatedAsyncioTestCase):
    async def test_reads_docs_and_utf8_files(self):
        service = SimpleNamespace(
            read_doc=AsyncMock(return_value="document"),
            read_file=AsyncMock(return_value="citation".encode()),
        )
        self.assertEqual(await read_entity_text(service, None, "p", "main.tex", "doc", "main"), "document")
        self.assertEqual(await read_entity_text(service, None, "p", "refs.bib", "file", "refs"), "citation")

    async def test_rejects_folders_and_skips_binary_files(self):
        service = SimpleNamespace(read_file=AsyncMock(return_value=b"\xff\xfe"))
        with self.assertRaisesRegex(FilesError, "is a folder"):
            await read_entity_text(service, None, "p", "chapters", "folder", "folder")
        self.assertIsNone(await try_read_entity_text(service, None, "p", "figure.png", "file", "image"))


class FilesComponentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.file = SimpleNamespace(
            read_doc=AsyncMock(return_value="body"),
            read_file=AsyncMock(return_value=b"@book{x}"),
            create_doc=AsyncMock(return_value=SimpleNamespace(id="created")),
            rename_entity=AsyncMock(),
            move_entity=AsyncMock(),
            refresh_linked_file=AsyncMock(),
            delete_entity=AsyncMock(),
        )
        self.realtime = SimpleNamespace(
            get_tree=AsyncMock(return_value=sample_tree()),
            replace_doc=AsyncMock(),
            patch_doc=AsyncMock(),
        )
        self.component = FilesComponent(self.file, self.realtime)

    async def test_lists_and_reads_all_entity_types(self):
        entries = await self.component.list_files(None, "p")
        self.assertEqual([(entry.name, entry.type) for entry in entries], [
            ("chapters", "folder"), ("main.tex", "doc"), ("refs.bib", "file"), ("figure.png", "file")
        ])
        content = await self.component.read_file(None, "p", "refs.bib")
        self.assertEqual(content.content, "@book{x}")
        self.assertEqual(content.linked_file_data, {"provider": "zotero"})

    async def test_creates_and_edits_documents(self):
        await self.component.create_file(None, "p", "chapters/new.tex", "hello")
        self.file.create_doc.assert_awaited_once_with(None, "p", "new.tex", "chapters")
        self.realtime.replace_doc.assert_awaited_once_with(None, "p", "created", "hello")

        await self.component.overwrite_file(None, "p", "main.tex", "replacement")
        await self.component.patch_file(None, "p", "main.tex", "old", "new")
        self.realtime.replace_doc.assert_awaited_with(None, "p", "main", "replacement")
        self.realtime.patch_doc.assert_awaited_once_with(None, "p", "main", "old", "new")

    async def test_rejects_duplicates_and_edits_to_file_entries(self):
        with self.assertRaisesRegex(FilesError, "already exists"):
            await self.component.create_file(None, "p", "main.tex")
        with self.assertRaisesRegex(FilesError, "not a document"):
            await self.component.overwrite_file(None, "p", "refs.bib", "replacement")


if __name__ == "__main__":
    unittest.main()
