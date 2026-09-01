import json
import os
import stat
from pathlib import Path

import keyring
import keyring.errors
from filelock import FileLock
from platformdirs import user_data_dir

from overleaf_mcp.models.credential import StoredCredential

_SERVICE_NAME = "overleaf-mcp"
_PROBE_KEY = "__overleaf_mcp_probe__"


class CredentialStoreService:
    """Cross-process store for session credentials, keyed by account identifier."""

    def __init__(self) -> None:
        data_dir = Path(user_data_dir(_SERVICE_NAME))
        data_dir.mkdir(parents=True, exist_ok=True)
        self._file_path = data_dir / "credentials.json"
        self._lock = FileLock(str(data_dir / "credentials.lock"))
        self._use_keyring = self._probe_keyring()

    def get(self, account: str) -> StoredCredential | None:
        with self._lock:
            raw = self._read(account)
        return StoredCredential.model_validate_json(raw) if raw is not None else None

    def set(self, account: str, credential: StoredCredential) -> None:
        with self._lock:
            self._write(account, credential.model_dump_json())

    def delete(self, account: str) -> None:
        with self._lock:
            self._delete(account)

    def _probe_keyring(self) -> bool:
        try:
            keyring.set_password(_SERVICE_NAME, _PROBE_KEY, "probe")
            keyring.delete_password(_SERVICE_NAME, _PROBE_KEY)
            return True
        except keyring.errors.KeyringError:
            return False

    def _read(self, account: str) -> str | None:
        if self._use_keyring:
            return keyring.get_password(_SERVICE_NAME, account)
        return self._load_file().get(account)

    def _write(self, account: str, raw: str) -> None:
        if self._use_keyring:
            keyring.set_password(_SERVICE_NAME, account, raw)
            return
        store = self._load_file()
        store[account] = raw
        self._save_file(store)

    def _delete(self, account: str) -> None:
        if self._use_keyring:
            try:
                keyring.delete_password(_SERVICE_NAME, account)
            except keyring.errors.PasswordDeleteError:
                pass
            return
        store = self._load_file()
        store.pop(account, None)
        self._save_file(store)

    def _load_file(self) -> dict[str, str]:
        if not self._file_path.exists():
            return {}
        return json.loads(self._file_path.read_text())

    def _save_file(self, store: dict[str, str]) -> None:
        self._file_path.write_text(json.dumps(store))
        os.chmod(self._file_path, stat.S_IRUSR | stat.S_IWUSR)
