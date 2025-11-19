"""Compat shim that re-exports the canonical `AtestadoHorasSystem` implementation."""

try:
    from ponto_esa_v5.atestado_horas_system import AtestadoHorasSystem  # type: ignore
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    # Placeholder class if import fails
    class AtestadoHorasSystem:
        pass

__all__ = ["AtestadoHorasSystem"]
