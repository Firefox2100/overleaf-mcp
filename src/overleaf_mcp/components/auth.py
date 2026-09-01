from overleaf_mcp.misc.config import Settings
from overleaf_mcp.models.credential import StoredCredential
from overleaf_mcp.models.overleaf_session import OverleafSession
from overleaf_mcp.services.credential import CredentialStoreService
from overleaf_mcp.services.overleaf.service import OverleafService


class AuthComponent:
    def __init__(self,
                 overleaf_service: OverleafService,
                 credential_store: CredentialStoreService,
                 settings: Settings,
                 ):
        self._overleaf = overleaf_service
        self._credentials = credential_store
        self._settings = settings

    def is_authenticated(self) -> bool:
        return self._credentials.get(self._settings.overleaf_email) is not None

    async def authenticate(self) -> OverleafSession:
        session = await self._overleaf.auth.init_session(
            self._settings.overleaf_email,
            self._settings.overleaf_password,
        )
        self._credentials.set(
            self._settings.overleaf_email,
            StoredCredential(
                cookies=session.cookies,
                csrf_token=session.csrf_token,
                updated_at=session.created_at,
            ),
        )
        return session

    async def ensure_session(self) -> OverleafSession:
        """
        Return the current session, authenticating first if none is stored.
        :return:
        """
        stored = self._credentials.get(self._settings.overleaf_email)
        if stored is None:
            return await self.authenticate()
        return self._session_from_stored(stored)

    async def logout(self) -> None:
        stored = self._credentials.get(self._settings.overleaf_email)
        if stored is None:
            return
        session = self._session_from_stored(stored)
        await self._overleaf.auth.destroy_session(session)
        self._credentials.delete(self._settings.overleaf_email)

    def _session_from_stored(self, stored: StoredCredential) -> OverleafSession:
        return OverleafSession(
            cookies=stored.cookies,
            csrf_token=stored.csrf_token or "",
            email=self._settings.overleaf_email,
            created_at=stored.updated_at,
        )
