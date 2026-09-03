from typing import Literal

from httpx import AsyncClient

from overleaf_mcp.models.overleaf_session import OverleafSession

PandocFormat = Literal["docx", "markdown", "html"]
PandocImportType = Literal["docx", "markdown"]


class OverleafPandocError(Exception):
    """Raised when Overleaf rejects a Pandoc conversion operation (CEP)."""


class OverleafPandocService:
    def __init__(self,
                 client: AsyncClient
                 ):
        self._client = client

    async def export_project(self, session: OverleafSession, project_id: str, format: PandocFormat) -> bytes:
        """
        Convert the whole project to docx, markdown, or html.
        :return:
        """
        response = await self._client.get(
            f"/project/{project_id}/download/conversion/{format}",
            params={"responseFormat": "stream"},
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafPandocError(f"Exporting project failed with status {response.status_code}: {response.text}")
        return response.content

    async def import_document(
            self,
            session: OverleafSession,
            project_name: str,
            doc_type: PandocImportType,
            filename: str,
            content: bytes,
    ) -> str:
        """
        Convert a document into a new project. Returns the new project's id.
        :return:
        """
        response = await self._client.post(
            "/project/new/import-document",
            params={"type": doc_type},
            data={"_csrf": session.csrf_token, "name": project_name},
            files={"qqfile": (filename, content)},
            headers={"Cookie": session.cookie_header, "X-Csrf-Token": session.csrf_token},
        )
        if response.status_code != 200:
            raise OverleafPandocError(f"Importing document failed with status {response.status_code}: {response.text}")
        body = response.json()
        if not body.get("success"):
            raise OverleafPandocError(f"Importing document failed: {body.get('error')}")
        return body["project_id"]
