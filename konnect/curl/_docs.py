# Copyright 2026  Dom Sekotill <dom.sekotill@kodo.org.uk>

from __future__ import annotations

import sys
from collections.abc import Callable

type Decorator[**P, R] = Callable[[Callable[P, R]], Callable[P, R]]

if "sphinx" in sys.modules:
	from deprecated.sphinx import deprecated

else:
	# No-op decorators to replace the "deprecated" package

	def deprecated[**P, R](reason: str, version: str = "") -> Decorator[P, R]:
		def decorator(func: Callable[P, R]) -> Callable[P, R]:
			return func

		return decorator


__all__ = ["deprecated"]
