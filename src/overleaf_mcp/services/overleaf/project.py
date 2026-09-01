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

    async def get_project(self, session: OverleafSession, project_id: str) -> Project:
        """
        Get a single project visible to the session's account.
        :return:
        """
        for project in await self.list_projects(session):
            if project.id == project_id:
                return project
        raise OverleafProjectError(f"Project {project_id} not found")

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

    async def delete_project(self, session: OverleafSession, project_id: str) -> None:
        """
        Soft-delete a project owned by the session's account. Overleaf moves it
        to a deleted-projects collection rather than purging it immediately.
        :return:
        """
        response = await self._client.delete(
            f"/project/{project_id}",
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafProjectError(f"Deleting project failed with status {response.status_code}: {response.text}")

    async def update_settings(
            self,
            session: OverleafSession,
            project_id: str,
            *,
            compiler: str | None = None,
            root_doc_id: str | None = None,
            main_bibliography_doc_id: str | None = None,
            spell_check_language: str | None = None,
    ) -> None:
        """
        Update project settings. Only fields passed as non-None are changed.
        :return:
        """
        body = {"_csrf": session.csrf_token}
        if compiler is not None:
            body["compiler"] = compiler
        if root_doc_id is not None:
            body["rootDocId"] = root_doc_id
        if main_bibliography_doc_id is not None:
            body["mainBibliographyDocId"] = main_bibliography_doc_id
        if spell_check_language is not None:
            body["spellCheckLanguage"] = spell_check_language

        response = await self._client.post(
            f"/project/{project_id}/settings",
            json=body,
            headers=session.auth_headers,
        )
        if response.status_code != 204:
            raise OverleafProjectError(f"Updating settings failed with status {response.status_code}: {response.text}")
