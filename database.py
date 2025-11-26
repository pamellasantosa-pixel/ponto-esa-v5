"""Shim de compatibilidade: reexporta `ponto_esa_v5.database` como `database`.

Permite que módulos que fazem `import database` continuem funcionando
quando o pacote principal está em `ponto_esa_v5`.
"""
try:
    from ponto_esa_v5.database import *  # type: ignore
    # Export __all__ if presente no módulo interno
    try:
        from ponto_esa_v5.database import __all__ as __ponto_all__  # type: ignore
        __all__ = __ponto_all__
    except Exception:
        __all__ = [name for name in globals() if not name.startswith('_')]
except Exception as _e:
    # Fallback leve: define funções mínimas para evitar que imports falhem
    def get_connection(*args, **kwargs):
        raise RuntimeError('database shim: módulo interno não disponível')

    def init_db(*args, **kwargs):
        raise RuntimeError('database shim: módulo interno não disponível')

    __all__ = ['get_connection', 'init_db']

# Importar a função get_connection do módulo database_postgresql
from ponto_esa_v5.database_postgresql import get_connection
