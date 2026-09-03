from typing import Literal

from fastmcp import Context, FastMCP
from mcp_types import ToolAnnotations

from overleaf_mcp.models.project_config import ProjectConfig

from .utils import get_config_component, get_overleaf_session, mounted_lifespan

config_mcp = FastMCP("config", lifespan=mounted_lifespan)


@config_mcp.tool(
    annotations=ToolAnnotations(
        title="Get Project Config",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def get_project_config(ctx: Context, project_id: str) -> ProjectConfig:
    """
    Get a project's compile-relevant configuration: compiler, root
    document, main bibliography document, spell-check language, and TeX
    Live image. A compile failure is sometimes caused by one of these
    being misconfigured rather than by the document content — in
    particular, a multi-file project with no root document set and no
    main.tex will fail to compile with "no main file specified".

    Args:
        project_id: Id of the project, as returned by list_projects.
    """
    config = get_config_component(ctx)
    session = get_overleaf_session(ctx)

    return await config.get_config(session, project_id)


@config_mcp.tool(
    annotations=ToolAnnotations(
        title="Set Compiler",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def set_compiler(
    ctx: Context,
    project_id: str,
    compiler: Literal["pdflatex", "xelatex", "lualatex", "latex"],
) -> None:
    """
    Set the LaTeX engine used to compile the project.

    Args:
        project_id: Id of the project, as returned by list_projects.
        compiler: LaTeX engine to compile with.
    """
    config = get_config_component(ctx)
    session = get_overleaf_session(ctx)

    await config.set_compiler(session, project_id, compiler)


@config_mcp.tool(
    annotations=ToolAnnotations(
        title="Set Root Document",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def set_root_document(ctx: Context, project_id: str, path: str) -> None:
    """
    Set the project's root document (the file compilation starts from —
    the one with \\documentclass). Required for a multi-file project
    with no doc named main.tex, or compilation fails with "no main file
    specified".

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "main.tex".
    """
    config = get_config_component(ctx)
    session = get_overleaf_session(ctx)

    await config.set_root_document(session, project_id, path)


@config_mcp.tool(
    annotations=ToolAnnotations(
        title="Set Main Bibliography Document",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def set_main_bibliography_document(ctx: Context, project_id: str, path: str) -> None:
    """
    Set the project's main bibliography document.

    Args:
        project_id: Id of the project, as returned by list_projects.
        path: Document path relative to the project root, e.g. "references.bib".
    """
    config = get_config_component(ctx)
    session = get_overleaf_session(ctx)

    await config.set_main_bibliography_document(session, project_id, path)


@config_mcp.tool(
    annotations=ToolAnnotations(
        title="Set Spell Check Language",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def set_spell_check_language(ctx: Context, project_id: str, language: str) -> None:
    """
    Set the project's spell-check dictionary language (e.g. "en_US").
    Cosmetic only — has no effect on compilation.

    Args:
        project_id: Id of the project, as returned by list_projects.
        language: Language code for the spell-check dictionary.
    """
    config = get_config_component(ctx)
    session = get_overleaf_session(ctx)

    await config.set_spell_check_language(session, project_id, language)


@config_mcp.tool(
    annotations=ToolAnnotations(
        title="Set Compile Image",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def set_compile_image(ctx: Context, project_id: str, image_name: str) -> None:
    """
    Set the TeX Live image the project compiles with, from
    get_project_config's available_images. Only has an effect where the
    server supports it (CEP with sandboxed compiles enabled) — raises
    otherwise, since the underlying setting is silently ignored rather
    than rejected when unsupported.

    Args:
        project_id: Id of the project, as returned by list_projects.
        image_name: Image to compile with, from get_project_config's available_images.
    """
    config = get_config_component(ctx)
    session = get_overleaf_session(ctx)

    await config.set_compile_image(session, project_id, image_name)
