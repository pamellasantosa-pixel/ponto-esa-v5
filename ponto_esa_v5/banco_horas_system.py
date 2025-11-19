"""Compat shim that re-exports the canonical `BancoHorasSystem` implementation."""

try:
    from ponto_esa_v5.banco_horas_system import BancoHorasSystem  # type: ignore
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(__file__))
    # Placeholder class if import fails
    class BancoHorasSystem:
        pass

__all__ = ["BancoHorasSystem"]
