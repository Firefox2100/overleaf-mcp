import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from overleaf_mcp.components.comment import CommentComponent, CommentError
from overleaf_mcp.components.config import ConfigComponent, ConfigError
from overleaf_mcp.components.review import ReviewComponent, ReviewError
from overleaf_mcp.models.project_config import ProjectConfig
from overleaf_mcp.models.project_tree import TreeEntity, TreeFolder


def tree() -> TreeFolder:
    return TreeFolder(
        id="root", name="root",
        docs=[TreeEntity(id="doc", name="main.tex")],
        file_refs=[TreeEntity(id="file", name="image.png")],
    )


class ConfigComponentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.project = SimpleNamespace(
            get_available_compile_images=AsyncMock(return_value=[]), update_settings=AsyncMock()
        )
        self.realtime = SimpleNamespace(
            get_tree=AsyncMock(return_value=tree()),
            get_project_info=AsyncMock(return_value=ProjectConfig(
                name="Project", compiler="pdflatex", root_doc_id="doc", root_doc_path="main.tex",
                spell_check_language="en", image_name="texlive", available_images=[],
            )),
        )
        self.component = ConfigComponent(self.project, self.realtime)

    async def test_gets_and_updates_all_settings(self):
        self.assertEqual((await self.component.get_config(None, "p")).compiler, "pdflatex")
        await self.component.set_compiler(None, "p", "xelatex")
        await self.component.set_root_document(None, "p", "main.tex")
        await self.component.set_main_bibliography_document(None, "p", "main.tex")
        await self.component.set_spell_check_language(None, "p", "fr")
        await self.component.set_compile_image(None, "p", "texlive")
        self.assertEqual(self.project.update_settings.await_count, 5)

    async def test_rejects_non_docs_and_ignored_compile_image(self):
        with self.assertRaisesRegex(ConfigError, "not a text document"):
            await self.component.set_root_document(None, "p", "image.png")
        self.realtime.get_project_info.return_value = self.realtime.get_project_info.return_value.model_copy(
            update={"image_name": "old"}
        )
        with self.assertRaisesRegex(ConfigError, "did not take effect"):
            await self.component.set_compile_image(None, "p", "new")


class ReviewComponentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.realtime = SimpleNamespace(
            get_tree=AsyncMock(return_value=tree()), replace_doc=AsyncMock(), patch_doc=AsyncMock(), reject_change=AsyncMock()
        )
        self.review = SimpleNamespace(
            set_track_changes=AsyncMock(), list_ranges=AsyncMock(), accept_changes=AsyncMock()
        )
        self.component = ReviewComponent(self.realtime, self.review)

    async def test_tracks_lists_accepts_and_rejects_changes(self):
        await self.component.set_track_changes(None, "p", True)
        await self.component.overwrite_file_tracked(None, "p", "main.tex", "new")
        await self.component.patch_file_tracked(None, "p", "main.tex", "old", "new")
        self.review.list_ranges.return_value = [{
            "id": "doc", "ranges": {"changes": [
                {"id": "insert", "op": {"p": 2, "i": "new"}, "metadata": {"user_id": "u", "ts": "1"}},
                {"id": "delete", "op": {"p": 1, "d": "old"}, "metadata": {"user_id": "u", "ts": "2"}},
            ]}
        }]
        changes = await self.component.list_tracked_changes(None, "p", "main.tex")
        self.assertEqual([change.type for change in changes], ["insert", "delete"])
        await self.component.accept_tracked_changes(None, "p", "main.tex", ["insert"])
        await self.component.reject_tracked_changes(None, "p", "main.tex", ["delete", "insert"])
        self.assertEqual(self.realtime.reject_change.await_count, 2)

    async def test_reports_unknown_changes_and_non_documents(self):
        self.review.list_ranges.return_value = []
        with self.assertRaisesRegex(ReviewError, "No tracked change"):
            await self.component.reject_tracked_changes(None, "p", "main.tex", ["missing"])
        with self.assertRaisesRegex(ReviewError, "not a text document"):
            await self.component.overwrite_file_tracked(None, "p", "image.png", "x")


class CommentComponentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.realtime = SimpleNamespace(get_tree=AsyncMock(return_value=tree()), add_comment=AsyncMock())
        self.review = SimpleNamespace(
            list_ranges=AsyncMock(return_value=[]), list_threads=AsyncMock(return_value={}),
            post_message=AsyncMock(), resolve_thread=AsyncMock(), reopen_thread=AsyncMock(), delete_thread=AsyncMock(),
        )
        self.file = SimpleNamespace(read_doc=AsyncMock(return_value="one unique phrase"))
        self.component = CommentComponent(self.realtime, self.review, self.file)

    async def test_comment_lifecycle_and_listing(self):
        with patch("overleaf_mcp.components.comment.secrets.token_hex", return_value="thread"):
            self.assertEqual(await self.component.create_comment(None, "p", "main.tex", "unique", "hello"), "thread")
        await self.component.reply_comment(None, "p", "thread", "reply")
        await self.component.resolve_comment(None, "p", "main.tex", "thread")
        await self.component.reopen_comment(None, "p", "main.tex", "thread")
        await self.component.delete_comment(None, "p", "main.tex", "thread")

        self.review.list_ranges.return_value = [{"id": "doc", "ranges": {"comments": [{"op": {"t": "thread", "c": "unique"}}]}}]
        self.review.list_threads.return_value = {"thread": {"resolved": False, "messages": []}, "orphan": {"resolved": True, "messages": []}}
        comments = await self.component.list_comments(None, "p")
        self.assertEqual({comment.id for comment in comments}, {"thread", "orphan"})
        self.assertEqual([comment.id for comment in await self.component.list_comments(None, "p", "main.tex")], ["thread"])

    async def test_validates_match_and_document(self):
        self.file.read_doc.return_value = "none"
        with self.assertRaisesRegex(CommentError, "No match"):
            await self.component.create_comment(None, "p", "main.tex", "missing", "x")
        self.file.read_doc.return_value = "twice twice"
        with self.assertRaisesRegex(CommentError, "not unique"):
            await self.component.create_comment(None, "p", "main.tex", "twice", "x")
        with self.assertRaisesRegex(CommentError, "not a text document"):
            await self.component.resolve_comment(None, "p", "image.png", "thread")


if __name__ == "__main__":
    unittest.main()
