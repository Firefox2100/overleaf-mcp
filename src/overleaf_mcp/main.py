import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastmcp import FastMCP

from overleaf_mcp.components.auth import AuthComponent
from overleaf_mcp.components.citation import CitationComponent
from overleaf_mcp.components.comment import CommentComponent
from overleaf_mcp.components.config import ConfigComponent
from overleaf_mcp.components.editing import EditingComponent
from overleaf_mcp.components.files import FilesComponent
from overleaf_mcp.components.pandoc import PandocComponent
from overleaf_mcp.components.review import ReviewComponent
from overleaf_mcp.misc.config import CONFIG
from overleaf_mcp.services.credential import CredentialStoreService
from overleaf_mcp.services.overleaf.capabilities import supports_review_mode
from overleaf_mcp.services.overleaf.service import OverleafService
from overleaf_mcp.tools.citation import citation_mcp
from overleaf_mcp.tools.compile import compile_mcp
from overleaf_mcp.tools.config import config_mcp
from overleaf_mcp.tools.editing import editing_mcp
from overleaf_mcp.tools.file import file_mcp
from overleaf_mcp.tools.github_sync import github_mcp
from overleaf_mcp.tools.history import history_mcp
from overleaf_mcp.tools.pandoc import pandoc_mcp
from overleaf_mcp.tools.project import project_mcp
from overleaf_mcp.tools.review import review_mcp
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

    review_component = None
    comment_component = None
    if await supports_review_mode(client):
        review_component = ReviewComponent(overleaf_service.realtime, overleaf_service.review)
        comment_component = CommentComponent(overleaf_service.realtime, overleaf_service.review, overleaf_service.file)
        server.mount(review_mcp, namespace="review")

    session = await auth_component.ensure_session()

    # githubSyncEnabled/enablePandocConversions have no dedicated capability
    # route (unlike review mode) — they're feature flags embedded in the
    # project editor page's bootstrap data, so detecting them needs an
    # actual project to load. If the account has none, these stay off.
    pandoc_component = None
    projects = await overleaf_service.project.list_projects(session)
    if projects:
        exposed_settings = await overleaf_service.project.get_exposed_settings(session, projects[0].id)
        if exposed_settings.get("githubSyncEnabled"):
            server.mount(github_mcp, namespace="github")
        if exposed_settings.get("enablePandocConversions"):
            pandoc_component = PandocComponent(
                overleaf_service.project, overleaf_service.file, overleaf_service.realtime, overleaf_service.pandoc,
            )
            server.mount(pandoc_mcp, namespace="pandoc")

    app_context = AppContext(
        overleaf_service=overleaf_service,
        credential_store=credential_store,
        auth_component=auth_component,
        files_component=files_component,
        editing_component=editing_component,
        config_component=config_component,
        citation_component=citation_component,
        overleaf_session=session,
        review_component=review_component,
        comment_component=comment_component,
        pandoc_component=pandoc_component,
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
    parser = argparse.ArgumentParser(prog="overleaf-mcp")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Serve over streamable HTTP instead of stdio.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind when using --http.")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind when using --http.")
    args = parser.parse_args()

    if args.http:
        mcp.run(transport="streamable-http", host=args.host, port=args.port)
    else:
        mcp.run()


if __name__ == "__main__":
    run()
