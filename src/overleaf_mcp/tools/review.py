from fastmcp import Context, FastMCP
from mcp_types import ToolAnnotations

from overleaf_mcp.models.comment import CommentThread
from overleaf_mcp.models.tracked_change import TrackedChange

from .utils import get_comment_component, get_overleaf_session, get_review_component, mounted_lifespan

review_mcp = FastMCP("review", lifespan=mounted_lifespan)


@review_mcp.tool(
    annotations=ToolAnnotations(
        title="Set Track Changes",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def set_track_changes(ctx: Context, project_id: str, enabled: bool) -> None:
    """
    Turn track changes (review mode) on or off for everyone on the
    project. While on, edits made with overwrite_file_tracked/
    patch_file_tracked are recorded as pending, attributed suggestions
    instead of being applied outright.

    Args:
        project_id: Id of the project, as returned by list_projects.
        enabled: Whether track changes should be on.
    """
    review = get_review_component(ctx)
    session = get_overleaf_session(ctx)

    await review.set_track_changes(session, project_id, enabled)


@review_mcp.tool(
    annotations=ToolAnnotations(
        title="Overwrite File Tracked",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def overwrite_file_tracked(ctx: Context, project_id: str, path: str, content: str) -> None:
    """
    Replace a text document's entire content as a tracked change (a
    pending, attributed suggestion, not applied outright) — the review-
    mode counterpart to the file tool set's overwrite_file. The whole old
    content is recorded as deleted and the new content as inserted, which
    is coarse; patch_file_tracked's targeted edit tracks more precisely.
    Does not require track changes to already be on for the project.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "chapters/intro.tex".
        content: New content for the document, replacing everything currently there.
    """
    review = get_review_component(ctx)
    session = get_overleaf_session(ctx)

    await review.overwrite_file_tracked(session, project_id, path, content)


@review_mcp.tool(
    annotations=ToolAnnotations(
        title="Patch File Tracked",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def patch_file_tracked(ctx: Context, project_id: str, path: str, find: str, replace: str) -> None:
    """
    Replace the single occurrence of exact text in a document as a
    tracked change (a pending, attributed suggestion, not applied
    outright) — the review-mode counterpart to the file tool set's
    patch_file. `find` must occur exactly once in the document's current
    content. Does not require track changes to already be on for the
    project.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "chapters/intro.tex".
        find: Exact text to find; must be unique in the document.
        replace: Text to replace it with.
    """
    review = get_review_component(ctx)
    session = get_overleaf_session(ctx)

    await review.patch_file_tracked(session, project_id, path, find, replace)


@review_mcp.tool(
    annotations=ToolAnnotations(
        title="List Tracked Changes",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def list_tracked_changes(ctx: Context, project_id: str, path: str | None = None) -> list[TrackedChange]:
    """
    List pending tracked changes across the project, or just in one
    document if path is given.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "chapters/intro.tex". Every document if omitted.
    """
    review = get_review_component(ctx)
    session = get_overleaf_session(ctx)

    return await review.list_tracked_changes(session, project_id, path)


@review_mcp.tool(
    annotations=ToolAnnotations(
        title="Accept Tracked Changes",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def accept_tracked_changes(ctx: Context, project_id: str, path: str, change_ids: list[str]) -> None:
    """
    Accept a document's tracked changes, applying them permanently.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "chapters/intro.tex".
        change_ids: Ids of the tracked changes to accept, from list_tracked_changes.
    """
    review = get_review_component(ctx)
    session = get_overleaf_session(ctx)

    await review.accept_tracked_changes(session, project_id, path, change_ids)


@review_mcp.tool(
    annotations=ToolAnnotations(
        title="Reject Tracked Changes",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def reject_tracked_changes(ctx: Context, project_id: str, path: str, change_ids: list[str]) -> None:
    """
    Reject a document's tracked changes, undoing them.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "chapters/intro.tex".
        change_ids: Ids of the tracked changes to reject, from list_tracked_changes.
    """
    review = get_review_component(ctx)
    session = get_overleaf_session(ctx)

    await review.reject_tracked_changes(session, project_id, path, change_ids)


@review_mcp.tool(
    annotations=ToolAnnotations(
        title="List Comments",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def list_comments(ctx: Context, project_id: str, path: str | None = None) -> list[CommentThread]:
    """
    List comment threads across the project, or just in one document if
    path is given.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "chapters/intro.tex". Every document if omitted.
    """
    comments = get_comment_component(ctx)
    session = get_overleaf_session(ctx)

    return await comments.list_comments(session, project_id, path)


@review_mcp.tool(
    annotations=ToolAnnotations(
        title="Create Comment",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def create_comment(ctx: Context, project_id: str, path: str, find: str, content: str) -> str:
    """
    Anchor a new comment thread to the single occurrence of exact text in
    a document and post its first message. Returns the new thread id.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "chapters/intro.tex".
        find: Exact text to anchor the comment to; must be unique in the document.
        content: The comment's text.
    """
    comments = get_comment_component(ctx)
    session = get_overleaf_session(ctx)

    return await comments.create_comment(session, project_id, path, find, content)


@review_mcp.tool(
    annotations=ToolAnnotations(
        title="Reply Comment",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def reply_comment(ctx: Context, project_id: str, thread_id: str, content: str) -> None:
    """
    Reply to an existing comment thread.

    Args:
        project_id: Id of the project, as returned by list_projects.
        thread_id: Id of the thread to reply to, from list_comments or create_comment.
        content: The reply's text.
    """
    comments = get_comment_component(ctx)
    session = get_overleaf_session(ctx)

    await comments.reply_comment(session, project_id, thread_id, content)


@review_mcp.tool(
    annotations=ToolAnnotations(
        title="Resolve Comment",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def resolve_comment(ctx: Context, project_id: str, path: str, thread_id: str) -> None:
    """
    Mark a comment thread resolved.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path the thread is anchored in, relative to the project root.
        thread_id: Id of the thread to resolve, from list_comments.
    """
    comments = get_comment_component(ctx)
    session = get_overleaf_session(ctx)

    await comments.resolve_comment(session, project_id, path, thread_id)


@review_mcp.tool(
    annotations=ToolAnnotations(
        title="Reopen Comment",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def reopen_comment(ctx: Context, project_id: str, path: str, thread_id: str) -> None:
    """
    Reopen a resolved comment thread.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path the thread is anchored in, relative to the project root.
        thread_id: Id of the thread to reopen, from list_comments.
    """
    comments = get_comment_component(ctx)
    session = get_overleaf_session(ctx)

    await comments.reopen_comment(session, project_id, path, thread_id)


@review_mcp.tool(
    annotations=ToolAnnotations(
        title="Delete Comment",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def delete_comment(ctx: Context, project_id: str, path: str, thread_id: str) -> None:
    """
    Delete a comment thread entirely, including all its messages.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path the thread is anchored in, relative to the project root.
        thread_id: Id of the thread to delete, from list_comments.
    """
    comments = get_comment_component(ctx)
    session = get_overleaf_session(ctx)

    await comments.delete_comment(session, project_id, path, thread_id)
