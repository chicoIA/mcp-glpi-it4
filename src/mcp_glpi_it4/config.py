"""Configuração lida de variáveis de ambiente. Nenhuma credencial é hardcoded."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _env(name: str, default: str | None = None, required: bool = False) -> str | None:
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(
            f"Variável de ambiente obrigatória ausente: {name}. "
            f"Veja .env.example."
        )
    return val


def _default_audit_dir() -> str:
    """Pasta gravável para os logs de auditoria/erro.

    O Claude Desktop pode iniciar o servidor com um diretório de trabalho
    sem permissão de escrita (ex.: '/'). Por isso o padrão é uma pasta
    do usuário, criada sob demanda. Pode ser sobrescrita por GLPI_AUDIT_DIR.
    """
    return os.path.join(os.path.expanduser("~"), ".mcp-glpi-it4")


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_version: str
    client_id: str
    client_secret: str
    username: str
    password: str
    scope: str
    write_mode: str          # "dry_run" | "live"
    timeout: float
    max_retries: int
    audit_dir: str

    @property
    def token_url(self) -> str:
        return f"{self.base_url}/api.php/token"

    @property
    def api_url(self) -> str:
        return f"{self.base_url}/api.php/{self.api_version}"

    @property
    def dry_run(self) -> bool:
        return self.write_mode.lower() != "live"

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            base_url=_env("GLPI_BASE_URL", "https://suporte.sys.it4solucao.com.br").rstrip("/"),
            api_version=_env("GLPI_API_VERSION", "v2.3"),
            client_id=_env("GLPI_CLIENT_ID", required=True),
            client_secret=_env("GLPI_CLIENT_SECRET", required=True),
            username=_env("GLPI_USERNAME", required=True),
            password=_env("GLPI_PASSWORD", required=True),
            scope=_env("GLPI_OAUTH_SCOPE", "api"),
            write_mode=_env("GLPI_WRITE_MODE", "dry_run"),
            timeout=float(_env("GLPI_TIMEOUT", "15")),
            max_retries=int(_env("GLPI_MAX_RETRIES", "3")),
            audit_dir=_env("GLPI_AUDIT_DIR", _default_audit_dir()),
        )
