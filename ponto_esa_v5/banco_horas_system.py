"""Compat shim that re-exports the canonical `BancoHorasSystem` implementation."""

try:
    from ponto_esa_v5.ponto_esa_v5.banco_horas_system import BancoHorasSystem  # type: ignore
except Exception:  # pragma: no cover - fallback for editable installs
    from ponto_esa_v5.banco_horas_system import BancoHorasSystem  # type: ignore

__all__ = ["BancoHorasSystem"]
