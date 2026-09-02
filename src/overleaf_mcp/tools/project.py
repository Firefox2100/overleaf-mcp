from pathlib import Path
from typing import Literal

from fastmcp import Context, FastMCP
from mcp_types import ToolAnnotations

from overleaf_mcp.models.collaborator import Collaborator
from overleaf_mcp.models.download import DownloadedFile
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


@project_mcp.tool(
    annotations=ToolAnnotations(
        title="Clone Project",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def clone_project(ctx: Context, project_id: str, name: str) -> CreatedProject:
    """
    Duplicate a project as a new one owned by the authenticated Overleaf
    account, e.g. to use it as a template.

    Args:
        project_id: Id of the project to clone, as returned by list_projects.
        name: Name for the new, cloned project.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.project.clone_project(session, project_id, name)


@project_mcp.tool(
    annotations=ToolAnnotations(
        title="Download Project Zip",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def download_project_zip(ctx: Context, project_id: str, destination_path: str) -> DownloadedFile:
    """
    Download the whole project as a zip archive and save it to a local
    path on the machine running this MCP server.

    Args:
        project_id: Id of the project, as returned by list_projects.
        destination_path: Local filesystem path to save the zip to. Parent directories are created if needed.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    content = await service.project.download_zip(session, project_id)

    destination = Path(destination_path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)

    return DownloadedFile(path=str(destination), size_bytes=len(content))


@project_mcp.tool(
    annotations=ToolAnnotations(
        title="List Collaborators",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def list_collaborators(ctx: Context, project_id: str) -> list[Collaborator]:
    """
    List a project's collaborators and their access level. Does not
    include the owner — see get_project for that.

    Args:
        project_id: Id of the project, as returned by list_projects.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.project.list_collaborators(session, project_id)
