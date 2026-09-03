import base64
from pathlib import Path
from typing import Literal

from fastmcp import Context, FastMCP
from mcp_types import ToolAnnotations

from overleaf_mcp.models.download import DownloadedFile

from .utils import get_overleaf_session, get_pandoc_component, mounted_lifespan

pandoc_mcp = FastMCP("pandoc", lifespan=mounted_lifespan)


@pandoc_mcp.tool(
    annotations=ToolAnnotations(
        title="Export Project",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=True,
    ),
)
async def export_project(
    ctx: Context,
    project_id: str,
    format: Literal["docx", "markdown", "html"],
    destination_path: str,
) -> DownloadedFile:
    """
    Convert the whole project to docx, markdown, or html and save it to a
    local path on the machine running this MCP server.

    Args:
        project_id: Id of the project, as returned by list_projects.
        format: Output format.
        destination_path: Local filesystem path to save the file to. Parent directories are created if needed.
    """
    pandoc = get_pandoc_component(ctx)
    session = get_overleaf_session(ctx)

    content = await pandoc.export_project(session, project_id, format)

    destination = Path(destination_path).expanduser()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(content)

    return DownloadedFile(path=str(destination), size_bytes=len(content))


@pandoc_mcp.tool(
    annotations=ToolAnnotations(
        title="Import File",
        readOnlyHint=False,
        destructiveHint=False,
        idempotentHint=False,
        openWorldHint=True,
    ),
)
async def import_file(
    ctx: Context,
    project_id: str,
    destination_folder: str,
    filename: str,
    content_base64: str,
) -> list[str]:
    """
    Add a file to a project. A .docx or .md file is converted to
    Overleaf-native content first, landing as one or more files in
    destination_folder (e.g. a .tex file plus any extracted images);
    anything else (.tex, images, etc.) is added as-is under that name.
    The general-purpose way to bring any file into a project — prefer
    this over create_file/create_linked_file when the server supports
    it, since it handles conversion automatically.

    Args:
        project_id: Id of the project, as returned by list_projects.
        destination_folder: Folder the result lands in, relative to the project root. Must already exist.
        filename: Original filename, including extension — determines whether and how it's converted.
        content_base64: The file's content, base64-encoded.
    """
    pandoc = get_pandoc_component(ctx)
    session = get_overleaf_session(ctx)

    content = base64.b64decode(content_base64)
    return await pandoc.import_file(session, project_id, destination_folder, filename, content)
