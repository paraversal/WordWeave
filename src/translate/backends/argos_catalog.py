import json
import os
import time
from pathlib import Path

from ..routing import shortest_path
from ..types import Language, Pair

# Longest chain of models we will plan or run (src -> pivot -> dst). Argos models
# are English-centred, so two hops reach every language pair.
MAX_HOPS = 2


class ArgosCatalog:
    """Argos package index (what *can* be downloaded), cached on disk."""

    def __init__(self, cache_dir: Path, ttl: float = 24 * 3600):
        self._file = cache_dir / "index.json"
        self._ttl = ttl
        self._pairs: list[Pair] | None = None

    # --- public ---
    def pairs(self) -> list[Pair]:
        if self._pairs is None:
            self._pairs = [
                Pair(Language.parse(r["from"], r["from_name"]),
                     Language.parse(r["to"], r["to_name"]))
                for r in self._load()
            ]
        return self._pairs

    def languages(self) -> frozenset[Language]:
        return frozenset(l for p in self.pairs() for l in (p.src, p.dst))

    def route(self, src: Language, dst: Language, max_hops: int | None = MAX_HOPS):
        return shortest_path(self.pairs(), src, dst, max_hops)

    def installed(self) -> set[tuple[str, str]]:
        from argostranslate import package  # lazy: heavy import
        return {(p.from_code, p.to_code) for p in package.get_installed_packages()}

    # --- cache ---
    def _read(self) -> list[dict] | None:
        try:
            return json.loads(self._file.read_text())
        except (OSError, json.JSONDecodeError):
            return None

    def _load(self) -> list[dict]:
        if self._file.exists() and time.time() - self._file.stat().st_mtime < self._ttl:
            rows = self._read()
            if rows is not None:
                return rows
        try:
            from argostranslate import package
            package.update_package_index()  # network
            uniq = {(p.from_code, p.to_code): {
                        "from": p.from_code, "to": p.to_code,
                        "from_name": p.from_name, "to_name": p.to_name}
                    for p in package.get_available_packages()}
            rows = list(uniq.values())
        except Exception:
            stale = self._read()
            if stale is not None:
                return stale  # offline: stale beats nothing
            raise
        self._file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._file.with_name(f"{self._file.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(rows))
        os.replace(tmp, self._file)  # atomic
        return rows