from fastmcp import Context, FastMCP
from mcp_types import ToolAnnotations

from overleaf_mcp.models.editing import OutlineEntry, SearchMatch

from .utils import get_editing_component, get_overleaf_session, mounted_lifespan

editing_mcp = FastMCP("editing", lifespan=mounted_lifespan)


@editing_mcp.tool(
    annotations=ToolAnnotations(
        title="Search Project",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def search_project(ctx: Context, project_id: str, query: str, regex: bool = False) -> list[SearchMatch]:
    """
    Search every text document in a project for a plain substring or, if
    regex is set, a regular expression. Fetches and searches every
    document's content itself — Overleaf has no server-side project search.

    Args:
        project_id: Id of the project, as returned by list_projects.
        query: Text or regular expression to search for.
        regex: Treat query as a regular expression instead of a plain substring.
    """
    editing = get_editing_component(ctx)
    session = get_overleaf_session(ctx)

    return await editing.search_project(session, project_id, query, regex)


@editing_mcp.tool(
    annotations=ToolAnnotations(
        title="Search File",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def search_file(
    ctx: Context,
    project_id: str,
    path: str,
    query: str,
    regex: bool = False,
) -> list[SearchMatch]:
    """
    Search a single text document for a plain substring or, if regex is
    set, a regular expression.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "chapters/intro.tex".
        query: Text or regular expression to search for.
        regex: Treat query as a regular expression instead of a plain substring.
    """
    editing = get_editing_component(ctx)
    session = get_overleaf_session(ctx)

    return await editing.search_file(session, project_id, path, query, regex)


@editing_mcp.tool(
    annotations=ToolAnnotations(
        title="Get Outline",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def get_outline(ctx: Context, project_id: str, path: str) -> list[OutlineEntry]:
    """
    Get a document's section/subsection outline. A regex-based
    approximation of Overleaf's own client-side outline parser — doesn't
    filter out sectioning commands inside \\newcommand definitions, unwrap
    \\texorpdfstring, or include beamer frames.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "chapters/intro.tex".
    """
    editing = get_editing_component(ctx)
    session = get_overleaf_session(ctx)

    return await editing.get_outline(session, project_id, path)


@editing_mcp.tool(
    annotations=ToolAnnotations(
        title="Read Lines",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def read_lines(ctx: Context, project_id: str, path: str, start_line: int, end_line: int) -> str:
    """
    Read a range of lines (1-indexed, inclusive) from a text document,
    cat -n style (each line prefixed with its line number), so a large
    document doesn't need to be read in full.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "chapters/intro.tex".
        start_line: First line to include (1-indexed).
        end_line: Last line to include (1-indexed, inclusive).
    """
    editing = get_editing_component(ctx)
    session = get_overleaf_session(ctx)

    return await editing.read_lines(session, project_id, path, start_line, end_line)
