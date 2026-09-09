import unittest
from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from overleaf_mcp.main import lifespan
from overleaf_mcp.services.overleaf.project import OverleafProjectError


class LifespanAuthenticationTests(unittest.IsolatedAsyncioTestCase):
    async def test_startup_refreshes_an_expired_stored_session(self):
        old_session = SimpleNamespace(name="old")
        new_session = SimpleNamespace(name="new")
        project = SimpleNamespace(id="project-id")
        project_service = SimpleNamespace(
            list_projects=AsyncMock(
                side_effect=[
                    OverleafProjectError("forbidden", status_code=403),
                    [project],
                ]
            ),
            get_exposed_settings=AsyncMock(return_value={}),
        )
        overleaf_service = SimpleNamespace(
            project=project_service,
            file=Mock(),
            realtime=Mock(),
            review=Mock(),
            pandoc=Mock(),
        )
        auth_component = SimpleNamespace(
            ensure_session=AsyncMock(return_value=old_session),
            refresh=AsyncMock(return_value=(new_session, False)),
        )
        client = SimpleNamespace(aclose=AsyncMock())
        server = SimpleNamespace(mount=Mock())

        @asynccontextmanager
        async def fake_client(*args, **kwargs):
            yield client

        with (
            patch("overleaf_mcp.main.httpx.AsyncClient", return_value=client),
            patch("overleaf_mcp.main.OverleafService", return_value=overleaf_service),
            patch("overleaf_mcp.main.CredentialStoreService"),
            patch("overleaf_mcp.main.AuthComponent", return_value=auth_component),
            patch("overleaf_mcp.main.supports_review_mode", AsyncMock(return_value=False)),
        ):
            async with lifespan(server) as state:
                self.assertIs(state["app"].overleaf_session, new_session)

        auth_component.refresh.assert_awaited_once()
        self.assertEqual(project_service.list_projects.await_count, 2)
        project_service.get_exposed_settings.assert_awaited_once_with(
            new_session, "project-id"
        )


if __name__ == "__main__":
    unittest.main()
