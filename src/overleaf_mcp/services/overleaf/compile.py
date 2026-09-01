from httpx import AsyncClient

from overleaf_mcp.models.compile import CompileLogEntry, CompileResult
from overleaf_mcp.models.overleaf_session import OverleafSession

from .compile_log import parse_compile_log


class OverleafCompileError(Exception):
    """Raised when Overleaf rejects a compile or output-file request."""


class OverleafCompileService:
    def __init__(self,
                 client: AsyncClient
                 ):
        self._client = client

    async def compile(self, session: OverleafSession, project_id: str, draft: bool = False) -> CompileResult:
        """
        Compile a project.
        :return:
        """
        response = await self._client.post(
            f"/project/{project_id}/compile",
            params={"file_line_errors": "1"},
            json={"_csrf": session.csrf_token, "draft": draft},
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafCompileError(f"Compile request failed with status {response.status_code}: {response.text}")
        return CompileResult.model_validate_json(response.text)

    async def download_output_file(
            self,
            session: OverleafSession,
            project_id: str,
            build_id: str,
            filename: str,
            clsi_server_id: str | None = None,
    ) -> bytes:
        """
        Download a single artifact from a compile.
        :return:
        """
        response = await self._client.get(
            # Unlike the rest of the API, this route is served in a way
            # that's case-sensitive on "Project" (verified live: lowercase
            # 404s through nginx).
            f"/Project/{project_id}/build/{build_id}/output/{filename}",
            params={"clsiserverid": clsi_server_id} if clsi_server_id else {},
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafCompileError(f"Downloading {filename} failed with status {response.status_code}: {response.text}")
        return response.content

    async def get_log(
            self,
            session: OverleafSession,
            project_id: str,
            build_id: str,
            clsi_server_id: str | None = None,
    ) -> str:
        """
        Fetch a compile's raw log text.
        :return:
        """
        content = await self.download_output_file(session, project_id, build_id, "output.log", clsi_server_id)
        return content.decode("utf-8", errors="replace")

    async def get_errors(
            self,
            session: OverleafSession,
            project_id: str,
            build_id: str,
            clsi_server_id: str | None = None,
    ) -> list[CompileLogEntry]:
        """
        Fetch and parse a compile's log, returning just the errors.
        :return:
        """
        log = await self.get_log(session, project_id, build_id, clsi_server_id)
        return [entry for entry in parse_compile_log(log) if entry.level == "error"]
