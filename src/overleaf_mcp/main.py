from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastmcp import FastMCP

from overleaf_mcp.components.auth import AuthComponent
from overleaf_mcp.misc.config import CONFIG
from overleaf_mcp.services.credential import CredentialStoreService
from overleaf_mcp.services.overleaf.service import OverleafService
from overleaf_mcp.tools.project import project_mcp
from overleaf_mcp.tools.utils import AppContext, app_context_state, publish_app_context


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict]:
    client = httpx.AsyncClient(base_url=CONFIG.overleaf_base_url)
    overleaf_service = OverleafService(client)
    credential_store = CredentialStoreService()
    auth_component = AuthComponent(overleaf_service, credential_store, CONFIG)

    session = await auth_component.ensure_session()

    app_context = AppContext(
        overleaf_service=overleaf_service,
        credential_store=credential_store,
        auth_component=auth_component,
        overleaf_session=session,
    )
    publish_app_context(app_context)

    try:
        yield app_context_state(app_context)
    finally:
        await client.aclose()


mcp = FastMCP("overleaf-mcp", lifespan=lifespan)
mcp.mount(project_mcp, namespace="project")


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
