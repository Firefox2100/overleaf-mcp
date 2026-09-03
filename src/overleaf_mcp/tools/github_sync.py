from fastmcp import Context, FastMCP
from mcp_types import ToolAnnotations

from overleaf_mcp.models.github_sync import GitHubSyncState

from .utils import get_overleaf_service, get_overleaf_session, mounted_lifespan

github_mcp = FastMCP("github", lifespan=mounted_lifespan)


@github_mcp.tool(
    annotations=ToolAnnotations(
        title="Get Sync State",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def get_sync_state(ctx: Context, project_id: str) -> GitHubSyncState:
    """
    Get a project's GitHub-sync link state. merge_status "need-export"
    means the project isn't linked to a GitHub repo — linking/unlinking
    has to be done from the web UI, this bridge only triggers syncs on an
    already-linked project.

    Args:
        project_id: Id of the project, as returned by list_projects.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.github_sync.get_state(session, project_id)


@github_mcp.tool(
    annotations=ToolAnnotations(
        title="Trigger Sync",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def trigger_sync(ctx: Context, project_id: str, message: str = "Updates from Overleaf") -> dict:
    """
    Sync an already-linked project with its GitHub repo: pulls upstream
    commits, merges them into the project, then pushes. Fails if the
    project isn't linked — check get_sync_state first.

    Args:
        project_id: Id of the project, as returned by list_projects.
        message: Commit message for the merge.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.github_sync.trigger_sync(session, project_id, message)
