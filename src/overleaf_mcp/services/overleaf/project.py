import html
import json
import re

from httpx import AsyncClient

from overleaf_mcp.models.collaborator import Collaborator
from overleaf_mcp.models.compile_image import CompileImage
from overleaf_mcp.models.overleaf_session import OverleafSession
from overleaf_mcp.models.project import CreatedProject, Project, ProjectList

_IMAGE_NAMES_PATTERN = re.compile(r'<meta name="ol-imageNames"[^>]*content="(?P<content>[^"]*)"')
_EXPOSED_SETTINGS_PATTERN = re.compile(r'<meta name="ol-ExposedSettings"[^>]*content="(?P<content>[^"]*)"')


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
            image_name: str | None = None,
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
        if image_name is not None:
            body["imageName"] = image_name

        response = await self._client.post(
            f"/project/{project_id}/settings",
            json=body,
            headers=session.auth_headers,
        )
        if response.status_code != 204:
            raise OverleafProjectError(f"Updating settings failed with status {response.status_code}: {response.text}")

    async def clone_project(self, session: OverleafSession, project_id: str, name: str) -> CreatedProject:
        """
        Duplicate a project as a new one owned by the session's account.
        :return:
        """
        response = await self._client.post(
            f"/Project/{project_id}/clone",
            json={"_csrf": session.csrf_token, "projectName": name},
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafProjectError(f"Cloning project failed with status {response.status_code}: {response.text}")
        return CreatedProject.model_validate_json(response.text)

    async def download_zip(self, session: OverleafSession, project_id: str) -> bytes:
        """
        Download the whole project as a zip archive.
        :return:
        """
        response = await self._client.get(
            f"/Project/{project_id}/download/zip",
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafProjectError(f"Downloading project zip failed with status {response.status_code}: {response.text}")
        return response.content

    async def list_collaborators(self, session: OverleafSession, project_id: str) -> list[Collaborator]:
        """
        List a project's collaborators and their access level. Does not
        include the owner — see get_project for that.
        :return:
        """
        response = await self._client.get(
            f"/project/{project_id}/members",
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafProjectError(f"Listing collaborators failed with status {response.status_code}: {response.text}")
        return [Collaborator.model_validate(member) for member in response.json()["members"]]

    async def get_available_compile_images(self, session: OverleafSession, project_id: str) -> list[CompileImage]:
        """
        List the TeX Live images available to compile with (CEP sandboxed
        compiles). Empty on a server without that feature — there's no
        dedicated endpoint for this, it's bootstrap data embedded in the
        project editor page.
        :return:
        """
        response = await self._client.get(
            f"/project/{project_id}",
            headers=session.auth_headers,
            follow_redirects=False,
        )
        if response.status_code != 200:
            raise OverleafProjectError(f"Loading project page failed with status {response.status_code}: {response.text}")
        match = _IMAGE_NAMES_PATTERN.search(response.text)
        if not match:
            return []
        return [CompileImage.model_validate(image) for image in json.loads(html.unescape(match.group("content")))]

    async def get_exposed_settings(self, session: OverleafSession, project_id: str) -> dict:
        """
        Fetch server-exposed feature flags (e.g. CEP's githubSyncEnabled,
        zoteroEnabled, enablePandocConversions) from the project editor
        page's bootstrap data. No dedicated endpoint for this either.
        :return:
        """
        response = await self._client.get(
            f"/project/{project_id}",
            headers=session.auth_headers,
            follow_redirects=False,
        )
        if response.status_code != 200:
            raise OverleafProjectError(f"Loading project page failed with status {response.status_code}: {response.text}")
        match = _EXPOSED_SETTINGS_PATTERN.search(response.text)
        if not match:
            return {}
        return json.loads(html.unescape(match.group("content")))
