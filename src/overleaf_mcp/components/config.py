from overleaf_mcp.models.overleaf_session import OverleafSession
from overleaf_mcp.models.project_config import ProjectConfig
from overleaf_mcp.models.project_tree import resolve_entity
from overleaf_mcp.services.overleaf.project import OverleafProjectService
from overleaf_mcp.services.overleaf.realtime import OverleafRealtimeService


class ConfigError(Exception):
    """Raised when a project-config operation's arguments don't resolve."""


class ConfigComponent:
    def __init__(self,
                 project_service: OverleafProjectService,
                 realtime_service: OverleafRealtimeService,
                 ):
        self._project = project_service
        self._realtime = realtime_service

    async def get_config(self, session: OverleafSession, project_id: str) -> ProjectConfig:
        """
        Get a project's compile-relevant configuration.
        :return:
        """
        return await self._realtime.get_project_info(session, project_id)

    async def set_compiler(self, session: OverleafSession, project_id: str, compiler: str) -> None:
        """
        Set the LaTeX engine used to compile the project.
        :return:
        """
        await self._project.update_settings(session, project_id, compiler=compiler)

    async def set_root_document(self, session: OverleafSession, project_id: str, path: str) -> None:
        """
        Set the project's root document.
        :return:
        """
        doc_id = await self._resolve_doc(session, project_id, path)
        await self._project.update_settings(session, project_id, root_doc_id=doc_id)

    async def set_main_bibliography_document(self, session: OverleafSession, project_id: str, path: str) -> None:
        """
        Set the project's main bibliography document.
        :return:
        """
        doc_id = await self._resolve_doc(session, project_id, path)
        await self._project.update_settings(session, project_id, main_bibliography_doc_id=doc_id)

    async def set_spell_check_language(self, session: OverleafSession, project_id: str, language: str) -> None:
        """
        Set the project's spell-check dictionary language.
        :return:
        """
        await self._project.update_settings(session, project_id, spell_check_language=language)

    async def _resolve_doc(self, session: OverleafSession, project_id: str, path: str) -> str:
        tree = await self._realtime.get_tree(session, project_id)
        entity_type, entity_id = resolve_entity(tree, path)
        if entity_type != "doc":
            raise ConfigError(f"{path!r} is not a text document")
        return entity_id
