"""Stub de gerenciador de conexão (compatibilidade local).

Fornece uma classe simples `ConnectionManager` para evitar erros de import
quando o módulo real não estiver presente durante análise estática ou testes.
"""
from typing import Any

class ConnectionManager:
    def __init__(self, dsn: str | None = None):
        self.dsn = dsn

    def get_connection(self) -> Any:
        raise NotImplementedError("Use o módulo de banco de dados real para conexões")


__all__ = ["ConnectionManager"]
