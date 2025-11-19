"""Compat shim that re-exports the canonical `AtestadoHorasSystem` implementation."""

try:
    from ponto_esa_v5.ponto_esa_v5.atestado_horas_system import AtestadoHorasSystem  # type: ignore
except Exception:  # pragma: no cover - fallback for editable installs
    from ponto_esa_v5.atestado_horas_system import AtestadoHorasSystem  # type: ignore

__all__ = ["AtestadoHorasSystem"]
