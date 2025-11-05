"""Helper utilities for package-wide imports.

This package was originally authored to run modules as standalone scripts
located in the same directory, so several modules still use direct imports
such as ``import database_postgresql`` or ``from notifications import ...``.
When the package is imported (for example during automated tests) those
absolute imports resolve to top-level module names and would normally fail.

To keep backward compatibility while enabling package usage, we eagerly
import a short list of core modules and register them in ``sys.modules`` with
their historic simple names. That way both execution styles keep working.
"""

from __future__ import annotations

import importlib
import sys
from typing import Iterable


def _alias_modules(simple_names: Iterable[str]) -> None:
	"""Expose package modules under their legacy simple import names."""

	package_name = __name__

	for simple_name in simple_names:
		if simple_name in sys.modules:
			continue

		try:
			module = importlib.import_module(f"{package_name}.{simple_name}")
		except Exception:
			continue

		sys.modules.setdefault(simple_name, module)


_alias_modules(
	(
		"database_postgresql",
		"notifications",
	)
)


__all__ = [
	"notifications",
	"database_postgresql",
]
