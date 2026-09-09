import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from overleaf_mcp.components.auth import AuthComponent
from overleaf_mcp.models.credential import StoredCredential
from overleaf_mcp.models.overleaf_session import OverleafSession
from overleaf_mcp.tools.auth import refresh_authentication
from overleaf_mcp.tools.utils import app_context_state


class AuthComponentRefreshTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            overleaf_base_url="https://overleaf.example",
            overleaf_email="service@example.com",
            overleaf_password="secret",
        )
        self.credential_key = (
            "https://overleaf.example|service@example.com"
        )
        self.old_credential = StoredCredential(
            cookies={"overleaf.sid": "old"},
            csrf_token="old-csrf",
            updated_at=datetime.now(timezone.utc),
        )
        self.new_session = OverleafSession(
            cookies={"overleaf.sid": "new"},
            csrf_token="new-csrf",
            email="service@example.com",
            created_at=datetime.now(timezone.utc),
        )
        self.credentials = Mock()
        self.credentials.get.return_value = self.old_credential
        self.overleaf = SimpleNamespace(
            auth=SimpleNamespace(
                destroy_session=AsyncMock(),
                init_session=AsyncMock(return_value=self.new_session),
            )
        )
        self.component = AuthComponent(
            self.overleaf, self.credentials, self.settings
        )

    async def test_refresh_logs_out_clears_credentials_and_logs_in(self):
        session, remote_logout_succeeded = await self.component.refresh()

        self.assertIs(session, self.new_session)
        self.assertTrue(remote_logout_succeeded)
        self.overleaf.auth.destroy_session.assert_awaited_once()
        self.credentials.delete.assert_called_once_with(self.credential_key)
        self.overleaf.auth.init_session.assert_awaited_once_with(
            "service@example.com", "secret"
        )
        self.credentials.set.assert_called_once()

    async def test_refresh_reauthenticates_when_remote_logout_fails(self):
        self.overleaf.auth.destroy_session.side_effect = RuntimeError(
            "session expired"
        )

        session, remote_logout_succeeded = await self.component.refresh()

        self.assertIs(session, self.new_session)
        self.assertFalse(remote_logout_succeeded)
        self.credentials.delete.assert_called_once_with(self.credential_key)
        self.overleaf.auth.init_session.assert_awaited_once_with(
            "service@example.com", "secret"
        )

    async def test_refresh_authenticates_when_no_session_is_stored(self):
        self.credentials.get.return_value = None

        session, remote_logout_succeeded = await self.component.refresh()

        self.assertIs(session, self.new_session)
        self.assertFalse(remote_logout_succeeded)
        self.overleaf.auth.destroy_session.assert_not_awaited()
        self.credentials.delete.assert_not_called()
        self.overleaf.auth.init_session.assert_awaited_once_with(
            "service@example.com", "secret"
        )


class AuthToolTests(unittest.IsolatedAsyncioTestCase):
    async def test_refresh_replaces_the_running_context_session(self):
        old_session = OverleafSession(
            cookies={"overleaf.sid": "old"},
            csrf_token="old-csrf",
            email="service@example.com",
            created_at=datetime.now(timezone.utc),
        )
        new_session = OverleafSession(
            cookies={"overleaf.sid": "new"},
            csrf_token="new-csrf",
            email="service@example.com",
            created_at=datetime.now(timezone.utc),
        )
        auth_component = SimpleNamespace(
            refresh=AsyncMock(return_value=(new_session, False))
        )
        app_context = SimpleNamespace(
            auth_component=auth_component,
            overleaf_session=old_session,
        )
        ctx = SimpleNamespace(lifespan_context=app_context_state(app_context))

        result = await refresh_authentication(ctx)

        self.assertIs(app_context.overleaf_session, new_session)
        self.assertEqual(
            result,
            {
                "authenticated": True,
                "email": "service@example.com",
                "remote_logout_succeeded": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
