from typing import Literal

from fastmcp import Context, FastMCP
from mcp_types import ToolAnnotations

from overleaf_mcp.models.project import CreatedProject, Project

from .utils import get_overleaf_service, get_overleaf_session, mounted_lifespan

project_mcp = FastMCP("project", lifespan=mounted_lifespan)


@project_mcp.tool(
    annotations=ToolAnnotations(
        title="List Projects",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def list_projects(ctx: Context) -> list[Project]:
    """
    List the projects visible to the authenticated Overleaf account.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.project.list_projects(session)


@project_mcp.tool(
    annotations=ToolAnnotations(
        title="Get Project",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def get_project(ctx: Context, project_id: str) -> Project:
    """
    Get a single project by id.

    Args:
        project_id: Id of the project to fetch, as returned by list_projects.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.project.get_project(session, project_id)


@project_mcp.tool(
    annotations=ToolAnnotations(
        title="Create Project",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def create_project(
    ctx: Context,
    name: str,
    template: Literal["none", "example"] = "none",
) -> CreatedProject:
    """
    Create a new project owned by the authenticated Overleaf account.

    Args:
        name: Name for the new project.
        template: "example" seeds it with Overleaf's example project content, "none" creates it blank.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.project.create_project(session, name, template)


@project_mcp.tool(
    annotations=ToolAnnotations(
        title="Delete Project",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def delete_project(ctx: Context, project_id: str) -> None:
    """
    Delete a project owned by the authenticated Overleaf account. Overleaf
    soft-deletes it (recoverable for a grace period from the web UI) rather
    than purging it immediately.

    Args:
        project_id: Id of the project to delete, as returned by list_projects.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    await service.project.delete_project(session, project_id)
