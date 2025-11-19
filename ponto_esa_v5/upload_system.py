"""Compat shim that re-exports the canonical `UploadSystem` implementation."""

try:
    from ponto_esa_v5.ponto_esa_v5.upload_system import UploadSystem  # type: ignore
except Exception:  # pragma: no cover - fallback for editable installs
    from ponto_esa_v5.upload_system import UploadSystem  # type: ignore

__all__ = ["UploadSystem"]
