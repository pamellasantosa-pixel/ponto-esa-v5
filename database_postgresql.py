"""Shim de compatibilidade: reexporta `ponto_esa_v5.database_postgresql`.

Alguns módulos fazem `from database_postgresql import ...` (import sem package)
— este arquivo simplesmente repassa as definições do módulo dentro do pacote
`ponto_esa_v5` para manter compatibilidade durante testes e execução local.
"""
try:
    from ponto_esa_v5.database_postgresql import *  # type: ignore
    try:
        from ponto_esa_v5.database_postgresql import __all__ as __ponto_all__  # type: ignore
        __all__ = __ponto_all__
    except Exception:
        __all__ = [name for name in globals() if not name.startswith('_')]
except Exception as _e:
    def get_connection(*args, **kwargs):
        raise RuntimeError('database_postgresql shim: módulo interno não disponível')

    def init_db_postgresql(*args, **kwargs):
        raise RuntimeError('database_postgresql shim: módulo interno não disponível')

    __all__ = ['get_connection', 'init_db_postgresql']
