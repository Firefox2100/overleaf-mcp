from fastmcp import Context, FastMCP
from mcp_types import ToolAnnotations

from overleaf_mcp.models.history import DiffChunk, HistoryLabel, HistoryPage, RestoredEntity

from .utils import get_overleaf_service, get_overleaf_session, mounted_lifespan

history_mcp = FastMCP("history", lifespan=mounted_lifespan)


def _annotations(title: str, *, read_only: bool) -> ToolAnnotations:
    return ToolAnnotations(
        title=title,
        readOnlyHint=read_only,
        destructiveHint=False if not read_only else None,
        idempotentHint=True if read_only else False,
        openWorldHint=True,
    )


@history_mcp.tool(annotations=_annotations("List History", read_only=True))
async def list_history(
    ctx: Context,
    project_id: str,
    before: int | None = None,
    min_count: int | None = None,
) -> HistoryPage:
    """
    List a project's change history, most recent first.

    Args:
        project_id: Id of the project, as returned by list_projects.
        before: Fetch history older than this version (from a previous page's next_before_timestamp).
        min_count: Minimum number of updates to return per page.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.history.list_updates(session, project_id, before, min_count)


@history_mcp.tool(annotations=_annotations("Get Diff", read_only=True))
async def get_diff(ctx: Context, project_id: str, path: str, from_version: int, to_version: int) -> list[DiffChunk]:
    """
    Get a document's diff between two history versions. Version numbers
    come from list_history's from_v/to_v.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "chapters/intro.tex".
        from_version: Earlier version to diff from.
        to_version: Later version to diff to.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.history.get_diff(session, project_id, path, from_version, to_version)


@history_mcp.tool(annotations=_annotations("Restore File", read_only=False))
async def restore_file(ctx: Context, project_id: str, path: str, version: int) -> RestoredEntity:
    """
    Restore a file's content as of a past version. Non-destructive: adds
    the restored content as a new file alongside the current one (named
    e.g. "main (Restored on ...).tex") rather than overwriting it — use
    overwrite_file afterwards if you want it to replace the current file.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "chapters/intro.tex".
        version: History version to restore, from list_history's from_v/to_v.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.history.restore_file(session, project_id, path, version)


@history_mcp.tool(annotations=_annotations("List Labels", read_only=True))
async def list_labels(ctx: Context, project_id: str) -> list[HistoryLabel]:
    """
    List a project's labeled (named) history versions.

    Args:
        project_id: Id of the project, as returned by list_projects.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.history.list_labels(session, project_id)


@history_mcp.tool(annotations=_annotations("Create Label", read_only=False))
async def create_label(ctx: Context, project_id: str, comment: str, version: int) -> HistoryLabel:
    """
    Label a history version, e.g. to mark a known-good checkpoint before a
    risky edit.

    Args:
        project_id: Id of the project, as returned by list_projects.
        comment: Label text.
        version: History version to label, from list_history's from_v/to_v.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.history.create_label(session, project_id, comment, version)
