"""
Cliente XML-RPC para Odoo Online
Soporta autenticación por API Key (recomendado) o usuario/contraseña
"""

import xmlrpc.client
from typing import Any


class OdooClient:
    def __init__(self, url: str, db: str, username: str, api_key: str):
        self.url = url.rstrip("/")
        self.db = db
        self.username = username
        self.api_key = api_key
        self.uid: int | None = None

        self._common = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/common", allow_none=True)
        self._models = xmlrpc.client.ServerProxy(f"{self.url}/xmlrpc/2/object", allow_none=True)

    def authenticate(self) -> int:
        """Autentica y retorna el uid del usuario."""
        self.uid = self._common.authenticate(self.db, self.username, self.api_key, {})
        if not self.uid:
            raise ConnectionError(
                "No se pudo autenticar con Odoo. Revisa URL, base de datos, usuario y API key."
            )
        return self.uid

    def ensure_auth(self):
        if self.uid is None:
            self.authenticate()

    def search_read(
        self,
        model: str,
        domain: list,
        fields: list[str],
        limit: int = 20,
        order: str = "",
    ) -> list[dict]:
        self.ensure_auth()
        kwargs: dict[str, Any] = {"fields": fields, "limit": limit}
        if order:
            kwargs["order"] = order
        return self._models.execute_kw(
            self.db, self.uid, self.api_key, model, "search_read", [domain], kwargs
        )

    def read(self, model: str, ids: list[int], fields: list[str]) -> list[dict]:
        self.ensure_auth()
        return self._models.execute_kw(
            self.db, self.uid, self.api_key, model, "read", [ids], {"fields": fields}
        )

    def create(self, model: str, values: dict) -> int:
        self.ensure_auth()
        return self._models.execute_kw(
            self.db, self.uid, self.api_key, model, "create", [values]
        )

    def write(self, model: str, ids: list[int], values: dict) -> bool:
        self.ensure_auth()
        return self._models.execute_kw(
            self.db, self.uid, self.api_key, model, "write", [ids, values]
        )

    def call(self, model: str, method: str, ids: list[int], kwargs: dict | None = None) -> bool:
        """
        Call any Odoo model method (e.g. button_draft, action_post).
        Discards the return value — methods like action_post return window-action
        dicts that may contain None, which XML-RPC cannot serialize.
        """
        self.ensure_auth()
        try:
            self._models.execute_kw(
                self.db, self.uid, self.api_key, model, method, [ids], kwargs or {}
            )
        except Exception as exc:
            # Ignore xmlrpc.client.Fault about None/marshalling — the call itself succeeded
            if "cannot marshal" not in str(exc) and "NoneType" not in str(exc):
                raise
        return True

    def execute(self, model: str, method: str, args: list, kwargs: dict | None = None) -> Any:
        """
        General-purpose execute_kw with arbitrary positional args and kwargs.
        Use this for wizard calls, default_get, or any method that needs context.
        Silently discards return values that contain None (window actions, etc.).
        """
        self.ensure_auth()
        try:
            result = self._models.execute_kw(
                self.db, self.uid, self.api_key, model, method, args, kwargs or {}
            )
            return result
        except Exception as exc:
            if "cannot marshal" not in str(exc) and "NoneType" not in str(exc):
                raise
            return None

    def fields_get(self, model: str, attributes: list[str] | None = None) -> dict:
        self.ensure_auth()
        kwargs = {"attributes": attributes or ["string", "type", "selection"]}
        return self._models.execute_kw(
            self.db, self.uid, self.api_key, model, "fields_get", [], kwargs
        )

    def get_server_version(self) -> dict:
        return self._common.version()
