try:
    # Preferred: use the internal package module
    from ponto_esa_v5.ponto_esa_v5.horas_extras_system import HorasExtrasSystem  # type: ignore
except Exception:
    # Fallback to the package-level module
    from ponto_esa_v5.horas_extras_system import HorasExtrasSystem  # type: ignore

__all__ = ["HorasExtrasSystem"]
