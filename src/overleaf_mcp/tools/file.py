from fastmcp import Context, FastMCP
from mcp_types import ToolAnnotations

from overleaf_mcp.models.entity import FileEntry

from .utils import get_files_component, get_overleaf_session, mounted_lifespan

file_mcp = FastMCP("file", lifespan=mounted_lifespan)


@file_mcp.tool(
    annotations=ToolAnnotations(
        title="List Files",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def list_files(ctx: Context, project_id: str, path: str = "") -> list[FileEntry]:
    """
    List the immediate contents of a folder in a project.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Folder path relative to the project root, e.g. "chapters". Empty for the project root.
    """
    files = get_files_component(ctx)
    session = get_overleaf_session(ctx)

    return await files.list_files(session, project_id, path)


@file_mcp.tool(
    annotations=ToolAnnotations(
        title="Read File",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def read_file(ctx: Context, project_id: str, path: str, offset: int = 1, limit: int | None = None) -> str:
    """
    Read a text document's content. Only text documents (e.g. .tex, .bib)
    are supported, not binary files. For a large document, use offset/limit
    to avoid reading it in full, or use the editing tool set's read_lines
    for a line-numbered view better suited to targeted navigation.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "chapters/intro.tex".
        offset: 1-indexed line to start reading from.
        limit: Maximum number of lines to return. Unlimited if omitted.
    """
    if offset < 1:
        raise ValueError(f"offset must be >= 1, got {offset}")

    files = get_files_component(ctx)
    session = get_overleaf_session(ctx)

    content = await files.read_file(session, project_id, path)
    lines = content.split("\n")
    return "\n".join(lines[offset - 1:offset - 1 + limit if limit is not None else None])


@file_mcp.tool(
    annotations=ToolAnnotations(
        title="Create File",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def create_file(ctx: Context, project_id: str, path: str, content: str = "") -> None:
    """
    Create a new text document. The parent folder must already exist.
    Only text documents are supported, not binary files.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: New document's path relative to the project root, e.g. "chapters/intro.tex".
        content: Initial content for the document. Left empty if omitted.
    """
    files = get_files_component(ctx)
    session = get_overleaf_session(ctx)

    await files.create_file(session, project_id, path, content)


@file_mcp.tool(
    annotations=ToolAnnotations(
        title="Rename File",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def rename_file(ctx: Context, project_id: str, path: str, name: str) -> None:
    """
    Rename a doc or file in place, without moving it to a different folder.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Current path of the doc or file, relative to the project root.
        name: New name (not a path — the entity stays in the same folder).
    """
    files = get_files_component(ctx)
    session = get_overleaf_session(ctx)

    await files.rename_file(session, project_id, path, name)


@file_mcp.tool(
    annotations=ToolAnnotations(
        title="Move File",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def move_file(ctx: Context, project_id: str, path: str, destination_folder: str) -> None:
    """
    Move a doc or file into a different folder, keeping its name. Use
    rename_file instead to change its name without moving it.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Current path of the doc or file, relative to the project root.
        destination_folder: Target folder path relative to the project root. Empty string for the project root.
    """
    files = get_files_component(ctx)
    session = get_overleaf_session(ctx)

    await files.move_file(session, project_id, path, destination_folder)


@file_mcp.tool(
    annotations=ToolAnnotations(
        title="Overwrite File",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def overwrite_file(ctx: Context, project_id: str, path: str, content: str) -> None:
    """
    Replace a text document's entire content. If a concurrent edit is
    detected (this is a live co-editing platform), the write is verified
    after the fact and this raises rather than silently losing it — the
    document may already have a mixed-in result and should be re-read.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "chapters/intro.tex".
        content: New content for the document, replacing everything currently there.
    """
    files = get_files_component(ctx)
    session = get_overleaf_session(ctx)

    await files.overwrite_file(session, project_id, path, content)


@file_mcp.tool(
    annotations=ToolAnnotations(
        title="Patch File",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def patch_file(ctx: Context, project_id: str, path: str, find: str, replace: str) -> None:
    """
    Replace one occurrence of exact text in a document. `find` must occur
    exactly once in the document's current content, or this raises rather
    than guessing. Subject to the same concurrent-edit verification as
    overwrite_file.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "chapters/intro.tex".
        find: Exact text to find; must be unique in the document.
        replace: Text to replace it with.
    """
    files = get_files_component(ctx)
    session = get_overleaf_session(ctx)

    await files.patch_file(session, project_id, path, find, replace)


@file_mcp.tool(
    annotations=ToolAnnotations(
        title="Delete File",
        readOnlyHint=False,
        destructiveHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def delete_file(ctx: Context, project_id: str, path: str) -> None:
    """
    Delete a doc or file. Does not delete folders.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Path of the doc or file to delete, relative to the project root.
    """
    files = get_files_component(ctx)
    session = get_overleaf_session(ctx)

    await files.delete_file(session, project_id, path)
