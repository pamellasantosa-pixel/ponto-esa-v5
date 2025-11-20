"""Utilitários para Streamlit - Safe Download Button"""

import streamlit as st
import logging
from io import BytesIO


def _extract_bytes(data):
    """Garante que data seja bytes ou ByteIO: se for tupla, extrai o primeiro elemento."""
    # Se for tupla (por engano) com (bytes, meta), extrair os bytes
    if isinstance(data, tuple) and data:
        possible = data[0]
        if isinstance(possible, (bytes, bytearray, BytesIO)):
            return possible
    # Se for BytesIO, retornar seu conteúdo
    if hasattr(data, 'getvalue'):
        try:
            return data.getvalue()
        except Exception:
            pass
    # Se já for bytes-like, retornar
    if isinstance(data, (bytes, bytearray)):
        return data
    # No demais, retornar None
    return None


def safe_download_button(label: str, data, **kwargs):
    """Wrapper seguro para st.download_button que evita passar tuplas por engano.

    Usa uma heurística simples para extrair bytes se `data` for uma tupla
    (por ex. retornada por get_file_content sem unpack) ou um BytesIO.
    """
    safe_data = _extract_bytes(data)
    # Log when a tuple or unexpected format is passed (helps debugging production errors)
    if safe_data is not None and isinstance(data, tuple):
        logging.getLogger(__name__).warning("safe_download_button: received a tuple for 'data'; extracted bytes to proceed")
    if safe_data is None:
        # Mantém o comportamento de falha do Streamlit: se for None/strange, apenas chama a função
        return st.download_button(label=label, data=data, **kwargs)
    return st.download_button(label=label, data=safe_data, **kwargs)


__all__ = ['safe_download_button', '_extract_bytes']
