"""Shim de compatibilidade para importações diretas de `ajuste_registros_system`."""
try:
    from ponto_esa_v5.ajuste_registros_system import *  # type: ignore
    try:
        from ponto_esa_v5.ajuste_registros_system import __all__ as __ponto_all__  # type: ignore
        __all__ = __ponto_all__
    except Exception:
        __all__ = [name for name in globals() if not name.startswith('_')]
except Exception as exc:
    def __getattr__(name):
        raise ImportError(f"O shim de ajuste_registros_system não pode carregar o módulo interno: {exc}")