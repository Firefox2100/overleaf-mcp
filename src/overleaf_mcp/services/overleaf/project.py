from httpx import AsyncClient

from overleaf_mcp.models.overleaf_session import OverleafSession
from overleaf_mcp.models.project import CreatedProject, Project, ProjectList


class OverleafProjectError(Exception):
    """Raised when Overleaf rejects a project operation."""


class OverleafProjectService:
    def __init__(self,
                 client: AsyncClient
                 ):
        self._client = client

    async def list_projects(self, session: OverleafSession) -> list[Project]:
        """
        List the projects visible to the session's account.
        :return:
        """
        response = await self._client.post(
            "/api/project",
            json={"_csrf": session.csrf_token},
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafProjectError(f"Listing projects failed with status {response.status_code}: {response.text}")
        return ProjectList.model_validate_json(response.text).projects

    async def create_project(self, session: OverleafSession, name: str, template: str = "none") -> CreatedProject:
        """
        Create a new project owned by the session's account.
        :return:
        """
        response = await self._client.post(
            "/project/new",
            json={"_csrf": session.csrf_token, "projectName": name, "template": template},
            headers=session.auth_headers,
            follow_redirects=False,
        )
        if response.status_code != 200:
            raise OverleafProjectError(f"Creating project failed with status {response.status_code}: {response.text}")
        return CreatedProject.model_validate_json(response.text)
