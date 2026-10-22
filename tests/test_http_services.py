import json
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx

from overleaf_mcp.models.overleaf_session import OverleafSession
from overleaf_mcp.services.overleaf.auth import OverleafAuthError, OverleafAuthService
from overleaf_mcp.services.overleaf.capabilities import supports_review_mode
from overleaf_mcp.services.overleaf.compile import OverleafCompileError, OverleafCompileService
from overleaf_mcp.services.overleaf.file import OverleafFileError, OverleafFileService
from overleaf_mcp.services.overleaf.github_sync import OverleafGitHubSyncError, OverleafGitHubSyncService
from overleaf_mcp.services.overleaf.pandoc import OverleafPandocError, OverleafPandocService


def response(status=200, *, text="", content=b"", data=None, cookies=None):
    value = Mock(status_code=status, text=text, content=content, cookies=cookies or {})
    value.json.return_value = data
    value.raise_for_status.return_value = None
    return value


class ServiceTestCase(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.session = OverleafSession(
            cookies={"sid": "cookie"}, csrf_token="csrf", email="test@example.com",
            created_at=datetime.now(timezone.utc),
        )
        self.client = SimpleNamespace(get=AsyncMock(), post=AsyncMock(), delete=AsyncMock())


class AuthServiceTests(ServiceTestCase):
    async def test_login_and_logout(self):
        self.client.get.side_effect = [
            response(text='<meta name="ol-csrfToken" content="before">', cookies={"pre": "one"}),
            response(text='<meta name="ol-csrfToken" content="after">', cookies={"sid": "two"}),
        ]
        self.client.post.side_effect = [response(cookies={"sid": "one"}), response(status=302)]
        service = OverleafAuthService(self.client)
        session = await service.init_session("user@example.com", "secret")
        self.assertEqual(session.csrf_token, "after")
        self.assertEqual(session.cookies, {"pre": "one", "sid": "two"})
        await service.destroy_session(session)

    async def test_rejects_missing_csrf_and_failed_requests(self):
        with self.assertRaisesRegex(OverleafAuthError, "CSRF token"):
            OverleafAuthService._extract_csrf_token("<html></html>")
        self.client.get.return_value = response(text='<meta name="ol-csrfToken" content="token">')
        self.client.post.return_value = response(status=401, text="denied")
        with self.assertRaisesRegex(OverleafAuthError, "Login failed"):
            await OverleafAuthService(self.client).init_session("user", "bad")
        self.client.post.return_value = response(status=500, text="error")
        with self.assertRaisesRegex(OverleafAuthError, "Logout failed"):
            await OverleafAuthService(self.client).destroy_session(self.session)


class CompileServiceTests(ServiceTestCase):
    async def test_compile_download_log_errors_and_word_count(self):
        service = OverleafCompileService(self.client)
        self.client.post.return_value = response(text=json.dumps({"status": "success", "output_files": []}))
        result = await service.compile(self.session, "project", draft=True)
        self.assertEqual(result.status, "success")

        self.client.get.return_value = response(content=b"main.tex:4: Broken command.\n")
        self.assertEqual(await service.get_log(self.session, "project", "build"), "main.tex:4: Broken command.\n")
        errors = await service.get_errors(self.session, "project", "build", "clsi")
        self.assertEqual((errors[0].file, errors[0].line), ("main.tex", 4))

        self.client.get.return_value = response(data={"texcount": {"encode": "utf8", "textWords": 12, "headWords": 2, "outside": 1, "headers": 1, "elements": 0, "mathInline": 0, "mathDisplay": 0, "errors": 0, "messages": ""}})
        count = await service.word_count(self.session, "project", "main.tex", "clsi")
        self.assertEqual(count.text_words, 12)

    async def test_reports_compile_download_and_wordcount_failures(self):
        service = OverleafCompileService(self.client)
        self.client.post.return_value = response(status=500, text="bad")
        with self.assertRaises(OverleafCompileError): await service.compile(self.session, "p")
        self.client.get.return_value = response(status=404, text="missing")
        with self.assertRaises(OverleafCompileError): await service.download_output_file(self.session, "p", "b", "x")
        with self.assertRaises(OverleafCompileError): await service.word_count(self.session, "p")


class FileServiceTests(ServiceTestCase):
    async def test_all_successful_file_operations(self):
        service = OverleafFileService(self.client)
        self.client.get.side_effect = [response(text="text"), response(content=b"bytes")]
        self.assertEqual(await service.read_doc(self.session, "p", "d"), "text")
        self.assertEqual(await service.read_file(self.session, "p", "f"), b"bytes")

        self.client.post.side_effect = [
            response(text='{"_id":"doc","name":"a.tex"}'),
            response(text='{"_id":"folder","name":"chapters"}'),
            response(text='{"success":true,"entity_id":"file","entity_type":"file"}'),
            response(data={"new_file_id": "linked"}), response(data={"new_file_id": "refreshed"}),
            response(status=204), response(status=204),
        ]
        self.assertEqual((await service.create_doc(self.session, "p", "a.tex", "root")).id, "doc")
        self.assertEqual((await service.create_folder(self.session, "p", "chapters")).id, "folder")
        self.assertTrue((await service.upload_file(self.session, "p", "root", "a.bin", b"x")).success)
        self.assertEqual(await service.create_linked_file(self.session, "p", "r.bib", "url", {"url": "x"}, "root"), "linked")
        self.assertEqual(await service.refresh_linked_file(self.session, "p", "linked"), "refreshed")
        await service.rename_entity(self.session, "p", "doc", "doc", "b.tex")
        await service.move_entity(self.session, "p", "doc", "doc", "folder")
        self.client.delete.return_value = response(status=204)
        await service.delete_entity(self.session, "p", "doc", "doc")

    async def test_every_operation_checks_status(self):
        service = OverleafFileService(self.client)
        bad = response(status=500, text="bad")
        self.client.get.return_value = bad; self.client.post.return_value = bad; self.client.delete.return_value = bad
        calls = [
            service.read_doc(self.session, "p", "d"), service.read_file(self.session, "p", "f"),
            service.create_doc(self.session, "p", "x"), service.create_folder(self.session, "p", "x"),
            service.upload_file(self.session, "p", "root", "x", b"x"),
            service.create_linked_file(self.session, "p", "x", "url", {}, "root"),
            service.refresh_linked_file(self.session, "p", "f"),
            service.rename_entity(self.session, "p", "doc", "d", "x"),
            service.move_entity(self.session, "p", "doc", "d", "root"),
            service.delete_entity(self.session, "p", "doc", "d"),
        ]
        for call in calls:
            with self.assertRaises(OverleafFileError): await call


class OptionalServiceTests(ServiceTestCase):
    async def test_capability_probe_handles_all_outcomes(self):
        self.client.get.side_effect = [response(status=403), response(status=404), httpx.ConnectError("offline")]
        self.assertTrue(await supports_review_mode(self.client))
        self.assertFalse(await supports_review_mode(self.client))
        self.assertFalse(await supports_review_mode(self.client))

    async def test_github_sync_success_and_failure(self):
        service = OverleafGitHubSyncService(self.client)
        self.client.get.return_value = response(text='{"mergeStatus":"clean","repoFullName":"org/repo"}')
        self.assertEqual((await service.get_state(self.session, "p")).merge_status, "clean")
        self.client.post.return_value = response(data={"ok": True})
        self.assertEqual(await service.trigger_sync(self.session, "p", "message"), {"ok": True})
        self.client.get.return_value = response(status=500, text="bad")
        with self.assertRaises(OverleafGitHubSyncError): await service.get_state(self.session, "p")
        self.client.post.return_value = response(status=500, text="bad")
        with self.assertRaises(OverleafGitHubSyncError): await service.trigger_sync(self.session, "p")

    async def test_pandoc_export_import_and_failures(self):
        service = OverleafPandocService(self.client)
        self.client.get.return_value = response(content=b"document")
        self.assertEqual(await service.export_project(self.session, "p", "docx"), b"document")
        self.client.post.return_value = response(data={"success": True, "project_id": "temporary"})
        self.assertEqual(await service.import_document(self.session, "name", "docx", "x.docx", b"x"), "temporary")
        self.client.get.return_value = response(status=500, text="bad")
        with self.assertRaises(OverleafPandocError): await service.export_project(self.session, "p", "html")
        self.client.post.return_value = response(status=500, text="bad")
        with self.assertRaises(OverleafPandocError): await service.import_document(self.session, "name", "docx", "x", b"x")


if __name__ == "__main__":
    unittest.main()
