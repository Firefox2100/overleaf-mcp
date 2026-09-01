from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass

from fastmcp import Context, FastMCP

from overleaf_mcp.components.auth import AuthComponent
from overleaf_mcp.components.citation import CitationComponent
from overleaf_mcp.components.config import ConfigComponent
from overleaf_mcp.components.editing import EditingComponent
from overleaf_mcp.components.files import FilesComponent
from overleaf_mcp.models.overleaf_session import OverleafSession
from overleaf_mcp.services.credential import CredentialStoreService
from overleaf_mcp.services.overleaf.service import OverleafService

_CONTEXT_KEY = "app"


@dataclass
class AppContext:
    overleaf_service: OverleafService
    credential_store: CredentialStoreService
    auth_component: AuthComponent
    files_component: FilesComponent
    editing_component: EditingComponent
    config_component: ConfigComponent
    citation_component: CitationComponent
    overleaf_session: OverleafSession


def app_context_state(app_context: AppContext) -> dict[str, AppContext]:
    return {_CONTEXT_KEY: app_context}


_published_app_context: AppContext | None = None


def publish_app_context(app_context: AppContext) -> None:
    """
    Publish the app context so mounted sub-servers' lifespans can pick it up.
    :return:
    """
    global _published_app_context
    _published_app_context = app_context


@asynccontextmanager
async def mounted_lifespan(server: FastMCP) -> AsyncIterator[dict]:
    """
    Lifespan for a mounted sub-server: reuses the app context published by the
    root server. A mounted server runs its own independent lifespan, so the
    root's yielded context isn't visible through it directly.
    :return:
    """
    if _published_app_context is None:
        raise RuntimeError("App context has not been published by the root server's lifespan")
    yield app_context_state(_published_app_context)


def get_app_context(ctx: Context) -> AppContext:
    return ctx.lifespan_context[_CONTEXT_KEY]


def get_overleaf_service(ctx: Context) -> OverleafService:
    return get_app_context(ctx).overleaf_service


def get_overleaf_session(ctx: Context) -> OverleafSession:
    return get_app_context(ctx).overleaf_session


def get_files_component(ctx: Context) -> FilesComponent:
    return get_app_context(ctx).files_component


def get_editing_component(ctx: Context) -> EditingComponent:
    return get_app_context(ctx).editing_component


def get_config_component(ctx: Context) -> ConfigComponent:
    return get_app_context(ctx).config_component


def get_citation_component(ctx: Context) -> CitationComponent:
    return get_app_context(ctx).citation_component
