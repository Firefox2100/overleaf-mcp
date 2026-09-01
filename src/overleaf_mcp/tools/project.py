from typing import Literal

from fastmcp import Context, FastMCP

from overleaf_mcp.models.project import CreatedProject, Project

from .utils import get_overleaf_service, get_overleaf_session, mounted_lifespan

project_mcp = FastMCP("project", lifespan=mounted_lifespan)


@project_mcp.tool
async def list_projects(ctx: Context) -> list[Project]:
    """
    List the projects visible to the authenticated Overleaf account.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.project.list_projects(session)


@project_mcp.tool
async def create_project(
    ctx: Context,
    name: str,
    template: Literal["none", "example"] = "none",
) -> CreatedProject:
    """
    Create a new project owned by the authenticated Overleaf account.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.project.create_project(session, name, template)
