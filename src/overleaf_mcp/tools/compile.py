from pathlib import Path

from fastmcp import Context, FastMCP
from mcp_types import ToolAnnotations

from overleaf_mcp.models.compile import CompileLogEntry, CompileResult, DownloadedFile

from .utils import get_overleaf_service, get_overleaf_session, mounted_lifespan

compile_mcp = FastMCP("compile", lifespan=mounted_lifespan)


@compile_mcp.tool(
    annotations=ToolAnnotations(
        title="Compile Project",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def compile_project(ctx: Context, project_id: str, draft: bool = False) -> CompileResult:
    """
    Compile a project. Each output file's `build` id is needed to fetch the
    log or PDF afterwards, with get_compile_log/get_compile_errors/get_output_file.

    Args:
        project_id: Id of the project, as returned by list_projects.
        draft: Use draft mode for a faster, lower-quality compile.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.compile.compile(session, project_id, draft)


@compile_mcp.tool(
    annotations=ToolAnnotations(
        title="Get Compile Log",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def get_compile_log(ctx: Context, project_id: str, build_id: str, clsi_server_id: str | None = None) -> str:
    """
    Fetch a compile's raw log text.

    Args:
        project_id: Id of the project, as returned by list_projects.
        build_id: Build id from a compile_project result's output_files.
        clsi_server_id: compile_project result's clsi_server_id, if set. Ensures this hits the same compile backend node.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.compile.get_log(session, project_id, build_id, clsi_server_id)


@compile_mcp.tool(
    annotations=ToolAnnotations(
        title="Get Compile Errors",
        readOnlyHint=True,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def get_compile_errors(
    ctx: Context,
    project_id: str,
    build_id: str,
    clsi_server_id: str | None = None,
) -> list[CompileLogEntry]:
    """
    Fetch a compile's log and return just the parsed errors (file, line,
    message where available). For the full log, including warnings, use
    get_compile_log.

    Args:
        project_id: Id of the project, as returned by list_projects.
        build_id: Build id from a compile_project result's output_files.
        clsi_server_id: compile_project result's clsi_server_id, if set. Ensures this hits the same compile backend node.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    return await service.compile.get_errors(session, project_id, build_id, clsi_server_id)


@compile_mcp.tool(
    annotations=ToolAnnotations(
        title="Get Output File",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def get_output_file(
    ctx: Context,
    project_id: str,
    build_id: str,
    destination_path: str,
    clsi_server_id: str | None = None,
) -> DownloadedFile:
    """
    Download a compile's output PDF and save it to a local path on the
    machine running this MCP server (not returned inline, since a PDF
    isn't something a model can usefully read from its raw bytes).

    Args:
        project_id: Id of the project, as returned by list_projects.
        build_id: Build id from a compile_project result's output_files.
        destination_path: Local filesystem path to save the PDF to. Parent directories are created if needed.
        clsi_server_id: compile_project result's clsi_server_id, if set. Ensures this hits the same compile backend node.
    """
    service = get_overleaf_service(ctx)
    session = get_overleaf_session(ctx)

    content = await service.compile.download_output_file(session, project_id, build_id, "output.pdf", clsi_server_id)

    destination = Path(destination_path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)

    return DownloadedFile(path=str(destination), size_bytes=len(content))
