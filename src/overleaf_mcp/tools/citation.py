from fastmcp import Context, FastMCP
from mcp_types import ToolAnnotations

from overleaf_mcp.models.citation import CitationCheckResult, CitationEntry
from overleaf_mcp.models.editing import SearchMatch

from .utils import get_citation_component, get_overleaf_session, mounted_lifespan

citation_mcp = FastMCP("citation", lifespan=mounted_lifespan)


def _read_only(title: str) -> ToolAnnotations:
    return ToolAnnotations(title=title, readOnlyHint=True, idempotentHint=True, openWorldHint=True)


@citation_mcp.tool(annotations=_read_only("List Citation Files"))
async def list_citation_files(ctx: Context, project_id: str) -> list[str]:
    """
    List every .bib file in a project, recursively.

    Args:
        project_id: Id of the project, as returned by list_projects.
    """
    citations = get_citation_component(ctx)
    session = get_overleaf_session(ctx)

    return await citations.list_citation_files(session, project_id)


@citation_mcp.tool(annotations=_read_only("List Citations"))
async def list_citations(ctx: Context, project_id: str, path: str | None = None) -> list[CitationEntry]:
    """
    List BibTeX entries. Reads every .bib file in the project, or just one
    if path is given.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: A specific .bib file's path, e.g. "references.bib". Every .bib file if omitted.
    """
    citations = get_citation_component(ctx)
    session = get_overleaf_session(ctx)

    return await citations.list_citations(session, project_id, path)


@citation_mcp.tool(annotations=_read_only("Find Citation"))
async def find_citation(ctx: Context, project_id: str, key: str) -> CitationEntry:
    """
    Find a BibTeX entry by its citation key.

    Args:
        project_id: Id of the project, as returned by list_projects.
        key: Citation key to look up, e.g. "smith2020".
    """
    citations = get_citation_component(ctx)
    session = get_overleaf_session(ctx)

    return await citations.find_citation(session, project_id, key)


@citation_mcp.tool(annotations=_read_only("Find Citation Usage"))
async def find_citation_usage(ctx: Context, project_id: str, key: str) -> list[SearchMatch]:
    """
    Find every \\cite-family command (\\cite, \\citep, \\citet, \\textcite,
    \\autocite, etc.) referencing a citation key, across the whole project.

    Args:
        project_id: Id of the project, as returned by list_projects.
        key: Citation key to search for, e.g. "smith2020".
    """
    citations = get_citation_component(ctx)
    session = get_overleaf_session(ctx)

    return await citations.find_citation_usage(session, project_id, key)


@citation_mcp.tool(annotations=_read_only("Check Citations"))
async def check_citations(ctx: Context, project_id: str) -> CitationCheckResult:
    """
    Cross-reference citation usage against BibTeX definitions across the
    whole project. Returns keys used in a \\cite-family command with no
    matching BibTeX entry (a common cause of a compile warning or a "?" in
    the PDF) and keys defined but never used.

    Args:
        project_id: Id of the project, as returned by list_projects.
    """
    citations = get_citation_component(ctx)
    session = get_overleaf_session(ctx)

    return await citations.check_citations(session, project_id)
