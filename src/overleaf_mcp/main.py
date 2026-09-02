from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastmcp import FastMCP

from overleaf_mcp.components.auth import AuthComponent
from overleaf_mcp.components.citation import CitationComponent
from overleaf_mcp.components.config import ConfigComponent
from overleaf_mcp.components.editing import EditingComponent
from overleaf_mcp.components.files import FilesComponent
from overleaf_mcp.misc.config import CONFIG
from overleaf_mcp.services.credential import CredentialStoreService
from overleaf_mcp.services.overleaf.service import OverleafService
from overleaf_mcp.tools.citation import citation_mcp
from overleaf_mcp.tools.compile import compile_mcp
from overleaf_mcp.tools.config import config_mcp
from overleaf_mcp.tools.editing import editing_mcp
from overleaf_mcp.tools.file import file_mcp
from overleaf_mcp.tools.history import history_mcp
from overleaf_mcp.tools.project import project_mcp
from overleaf_mcp.tools.utils import AppContext, app_context_state, publish_app_context


@asynccontextmanager
async def lifespan(server: FastMCP) -> AsyncIterator[dict]:
    client = httpx.AsyncClient(base_url=CONFIG.overleaf_base_url)
    overleaf_service = OverleafService(client)
    credential_store = CredentialStoreService()
    auth_component = AuthComponent(overleaf_service, credential_store, CONFIG)
    files_component = FilesComponent(overleaf_service.file, overleaf_service.realtime)
    editing_component = EditingComponent(files_component, overleaf_service.file, overleaf_service.realtime)
    config_component = ConfigComponent(overleaf_service.project, overleaf_service.realtime)
    citation_component = CitationComponent(overleaf_service.file, overleaf_service.realtime)

    session = await auth_component.ensure_session()

    app_context = AppContext(
        overleaf_service=overleaf_service,
        credential_store=credential_store,
        auth_component=auth_component,
        files_component=files_component,
        editing_component=editing_component,
        config_component=config_component,
        citation_component=citation_component,
        overleaf_session=session,
    )
    publish_app_context(app_context)

    try:
        yield app_context_state(app_context)
    finally:
        await client.aclose()


mcp = FastMCP("overleaf-mcp", lifespan=lifespan)
mcp.mount(project_mcp, namespace="project")
mcp.mount(file_mcp, namespace="file")
mcp.mount(compile_mcp, namespace="compile")
mcp.mount(editing_mcp, namespace="editing")
mcp.mount(config_mcp, namespace="config")
mcp.mount(citation_mcp, namespace="citation")
mcp.mount(history_mcp, namespace="history")


def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()
