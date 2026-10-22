import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import keyring.errors

from overleaf_mcp.components.pandoc import PandocComponent
from overleaf_mcp.models.credential import StoredCredential
from overleaf_mcp.models.project_tree import TreeEntity, TreeFolder
from overleaf_mcp.services.credential import CredentialStoreService


class CredentialStoreTests(unittest.TestCase):
    def credential(self):
        return StoredCredential(cookies={"sid": "x"}, csrf_token="token", updated_at=datetime.now(timezone.utc))

    def test_file_fallback_round_trip_and_permissions(self):
        with tempfile.TemporaryDirectory() as directory, patch(
            "overleaf_mcp.services.credential.user_data_dir", return_value=directory
        ), patch("overleaf_mcp.services.credential.keyring.set_password", side_effect=keyring.errors.KeyringError):
            store = CredentialStoreService()
            self.assertIsNone(store.get("account"))
            store.set("account", self.credential())
            self.assertEqual(store.get("account").csrf_token, "token")
            self.assertEqual(Path(directory, "credentials.json").stat().st_mode & 0o777, 0o600)
            store.delete("account")
            self.assertIsNone(store.get("account"))

    def test_keyring_round_trip_and_missing_delete(self):
        values = {}
        def set_password(_service, account, value): values[account] = value
        def get_password(_service, account): return values.get(account)
        def delete_password(_service, account):
            if account not in values: raise keyring.errors.PasswordDeleteError("missing")
            del values[account]
        with tempfile.TemporaryDirectory() as directory, patch(
            "overleaf_mcp.services.credential.user_data_dir", return_value=directory
        ), patch("overleaf_mcp.services.credential.keyring.set_password", side_effect=set_password), patch(
            "overleaf_mcp.services.credential.keyring.get_password", side_effect=get_password
        ), patch("overleaf_mcp.services.credential.keyring.delete_password", side_effect=delete_password):
            store = CredentialStoreService()
            store.set("account", self.credential())
            self.assertIsNotNone(store.get("account"))
            store.delete("account")
            store.delete("missing")


class PandocComponentTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.target = TreeFolder(id="target", name="root", folders=[TreeFolder(id="dest", name="dest")])
        self.source = TreeFolder(
            id="source", name="root",
            docs=[TreeEntity(id="doc", name="converted.tex")],
            file_refs=[TreeEntity(id="image", name="image.png")],
            folders=[TreeFolder(id="sub", name="assets", docs=[TreeEntity(id="nested", name="note.txt")])],
        )
        self.project = SimpleNamespace(delete_project=AsyncMock())
        self.file = SimpleNamespace(
            create_doc=AsyncMock(side_effect=lambda _s, _p, name, _f: SimpleNamespace(id=f"new-{name}")),
            create_folder=AsyncMock(side_effect=lambda _s, _p, name, _f: SimpleNamespace(id=f"new-{name}")),
            upload_file=AsyncMock(), read_doc=AsyncMock(return_value="content"), read_file=AsyncMock(return_value=b"image"),
        )
        self.realtime = SimpleNamespace(get_tree=AsyncMock(), replace_doc=AsyncMock())
        self.pandoc = SimpleNamespace(export_project=AsyncMock(return_value=b"export"), import_document=AsyncMock(return_value="temp"))
        self.component = PandocComponent(self.project, self.file, self.realtime, self.pandoc)

    async def test_exports_and_imports_plain_and_binary_files(self):
        self.assertEqual(await self.component.export_project(None, "p", "docx"), b"export")
        self.realtime.get_tree.return_value = self.target
        self.assertEqual(await self.component.import_file(None, "p", "dest", "notes.md", b"hello"), ["dest/notes.md"])
        self.assertEqual(await self.component.import_file(None, "p", "dest", "image.png", b"png"), ["dest/image.png"])
        self.realtime.replace_doc.assert_awaited()
        self.file.upload_file.assert_awaited()

    async def test_imports_converted_tree_and_always_deletes_temporary_project(self):
        self.realtime.get_tree.side_effect = [self.source, self.target]
        created = await self.component.import_file(None, "p", "dest", "paper.docx", b"docx")
        self.assertEqual(created, ["dest/converted.tex", "dest/image.png", "dest/assets/note.txt"])
        self.project.delete_project.assert_awaited_once_with(None, "temp")


if __name__ == "__main__":
    unittest.main()
