"""Backend registry. Backends are imported on demand.

Each entry is a small factory that imports its backend lazily, so choosing one
backend never pays the import cost of the others. Factories (unlike "module:Class"
strings) are real imports: a rename or typo fails loudly in linters and tests.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from translate.types import Backend


def _argos_stock(cache_dir: Path) -> "Backend":
    from translate.backends.argos_catalog import ArgosCatalog
    from translate.backends.argos_stock import StockArgos
    return StockArgos(ArgosCatalog(cache_dir))


def _argos_lean(cache_dir: Path) -> "Backend":
    from translate.backends.argos_catalog import ArgosCatalog
    from translate.backends.argos_lean import LeanArgos
    return LeanArgos(ArgosCatalog(cache_dir))


# Keys must match the values offered in info.plist's backend setting.
BACKENDS: dict[str, Callable[[Path], "Backend"]] = {
    "argosstock": _argos_stock,
    "argoslean": _argos_lean,
    # "googletrans": _googletrans,
}


def make_backend(name: str, cache_dir: Path) -> "Backend":
    try:
        factory = BACKENDS[name]
    except KeyError:
        raise ValueError(f"unknown backend {name!r}; choose from: {', '.join(BACKENDS)}") from None
    return factory(cache_dir)
