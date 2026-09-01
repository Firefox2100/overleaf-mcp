from httpx import AsyncClient

from overleaf_mcp.models.entity import CreatedEntity, EntityType, UploadedFile
from overleaf_mcp.models.overleaf_session import OverleafSession


class OverleafFileError(Exception):
    """Raised when Overleaf rejects a file or folder operation."""


class OverleafFileService:
    def __init__(self,
                 client: AsyncClient
                 ):
        self._client = client

    async def read_doc(self, session: OverleafSession, project_id: str, doc_id: str) -> str:
        """
        Read a doc's (text document's) current content.
        :return:
        """
        response = await self._client.get(
            f"/project/{project_id}/doc/{doc_id}/download",
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafFileError(f"Reading doc failed with status {response.status_code}: {response.text}")
        return response.text

    async def read_file(self, session: OverleafSession, project_id: str, file_id: str) -> bytes:
        """
        Read a file's (binary file's) current content.
        :return:
        """
        response = await self._client.get(
            f"/project/{project_id}/file/{file_id}",
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafFileError(f"Reading file failed with status {response.status_code}: {response.text}")
        return response.content

    async def create_doc(
            self,
            session: OverleafSession,
            project_id: str,
            name: str,
            parent_folder_id: str | None = None,
    ) -> CreatedEntity:
        """
        Create a new, empty doc (text document). Created at the project root
        when parent_folder_id is omitted.
        :return:
        """
        body = {"_csrf": session.csrf_token, "name": name}
        if parent_folder_id is not None:
            body["parent_folder_id"] = parent_folder_id
        response = await self._client.post(
            f"/project/{project_id}/doc",
            json=body,
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafFileError(f"Creating doc failed with status {response.status_code}: {response.text}")
        return CreatedEntity.model_validate_json(response.text)

    async def create_folder(
            self,
            session: OverleafSession,
            project_id: str,
            name: str,
            parent_folder_id: str | None = None,
    ) -> CreatedEntity:
        """
        Create a new folder. Created at the project root when
        parent_folder_id is omitted.
        :return:
        """
        body = {"_csrf": session.csrf_token, "name": name}
        if parent_folder_id is not None:
            body["parent_folder_id"] = parent_folder_id
        response = await self._client.post(
            f"/project/{project_id}/folder",
            json=body,
            headers=session.auth_headers,
        )
        if response.status_code != 200:
            raise OverleafFileError(f"Creating folder failed with status {response.status_code}: {response.text}")
        return CreatedEntity.model_validate_json(response.text)

    async def upload_file(
            self,
            session: OverleafSession,
            project_id: str,
            folder_id: str,
            name: str,
            content: bytes,
    ) -> UploadedFile:
        """
        Upload a binary file into a folder, creating it or overwriting an
        existing file of the same name in that folder.
        :return:
        """
        response = await self._client.post(
            f"/project/{project_id}/upload",
            params={"folder_id": folder_id},
            data={"_csrf": session.csrf_token, "name": name},
            files={"qqfile": (name, content)},
            headers={"Cookie": session.cookie_header, "X-Csrf-Token": session.csrf_token},
        )
        if response.status_code != 200:
            raise OverleafFileError(f"Uploading file failed with status {response.status_code}: {response.text}")
        return UploadedFile.model_validate_json(response.text)

    async def rename_entity(
            self,
            session: OverleafSession,
            project_id: str,
            entity_type: EntityType,
            entity_id: str,
            name: str,
    ) -> None:
        """
        Rename a doc, file, or folder in place.
        :return:
        """
        response = await self._client.post(
            f"/project/{project_id}/{entity_type}/{entity_id}/rename",
            json={"_csrf": session.csrf_token, "name": name},
            headers=session.auth_headers,
        )
        if response.status_code != 204:
            raise OverleafFileError(f"Renaming entity failed with status {response.status_code}: {response.text}")

    async def delete_entity(
            self,
            session: OverleafSession,
            project_id: str,
            entity_type: EntityType,
            entity_id: str,
    ) -> None:
        """
        Delete a doc, file, or folder.
        :return:
        """
        response = await self._client.delete(
            f"/project/{project_id}/{entity_type}/{entity_id}",
            headers=session.auth_headers,
        )
        if response.status_code != 204:
            raise OverleafFileError(f"Deleting entity failed with status {response.status_code}: {response.text}")
