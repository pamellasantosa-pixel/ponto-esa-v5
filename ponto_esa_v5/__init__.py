"""
Top-level package shim for tests and development.

This repository uses a nested package layout `ponto_esa_v5/ponto_esa_v5`.
To allow importing modules as `ponto_esa_v5.<module>` during tests
and development, extend the package __path__ to include the nested
subpackage directory at runtime.

This avoids ModuleNotFoundError when tests import e.g.:
	from ponto_esa_v5.streamlit_utils import _extract_bytes
"""
import os
__path__.append(os.path.join(os.path.dirname(__file__), "ponto_esa_v5"))
