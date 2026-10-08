"""Backend "googletrans": Google Translate via the googletrans package.

Unlike the Argos backends this one is online and has nothing to install, so:
  - load() has nothing to load; it only checks that Google supports the pair.
  - route() is always a single direct hop (Google pivots internally).
  - PairNotInstalled means "Google doesn't support this language", never "download it".
  - Failing to reach Google raises BackendUnavailable.

Supported languages: googletrans ships Google's language table as static data
(`googletrans.constants.LANGUAGES`), so languages() needs no network. The workflow
only accepts two-letter ISO 639-1 codes, so the table's 3-letter and regional entries
("ace", "zh-cn", ...) are dropped. The table is read straight from its file instead of
importing googletrans: that import pulls in httpx (~0.3 s) and languages() runs on
every keystroke in Alfred. Only translate() pays for the real import.

N-best: Google returns a single translation. For single words it also returns a
dictionary (`all-translations`: alternatives per part of speech, each with a
frequency). Those alternatives become the extra hypotheses, scored as log(frequency),
which is what ranks them against each other. Phrases and sentences get one hypothesis.
"""
from __future__ import annotations

import asyncio
import importlib.util
import math
from pathlib import Path
from typing import Any

from translate.errors import BackendUnavailable, PairNotInstalled
from translate.types import Hypothesis, Language, Pair

_SERVICE_URL = "translate.googleapis.com"  # the keyless "gtx" endpoint: no token round trip
_TIMEOUT = 5.0  # seconds; Alfred shouldn't hang on a dead connection
_MIN_SCORE = -30.0  # floor for log(frequency), in case Google reports 0


def _language_table() -> dict[str, str]:
    """googletrans's code -> name table, read without importing googletrans (see module doc)."""
    spec = importlib.util.find_spec("googletrans")  # locates the package without importing it
    if spec is None or not spec.submodule_search_locations:
        raise ModuleNotFoundError("googletrans is not installed")
    path = Path(next(iter(spec.submodule_search_locations))) / "constants.py"
    const_spec = importlib.util.spec_from_file_location("_googletrans_constants", path)
    assert const_spec is not None and const_spec.loader is not None
    module = importlib.util.module_from_spec(const_spec)
    const_spec.loader.exec_module(module)  # constants.py is plain data, no imports
    return module.LANGUAGES


def _log_score(frequency: Any) -> float:
    if isinstance(frequency, (int, float)) and frequency > 0:
        return max(math.log(frequency), _MIN_SCORE)
    return _MIN_SCORE


def _dictionary_entries(extra_data: dict | None) -> list[Hypothesis]:
    """Alternatives from Google's `all-translations` (single words only), most frequent first.

    Rows look like [word, [back-translations], None, frequency, ...], grouped by part of
    speech. A word listed under several parts of speech keeps its highest frequency.
    """
    best: dict[str, Hypothesis] = {}
    for part_of_speech in (extra_data or {}).get("all-translations") or []:
        for row in part_of_speech[2] or []:
            word = row[0]
            score = _log_score(row[3] if len(row) > 3 else None)
            key = word.casefold()
            if word and (key not in best or score > best[key].score):
                best[key] = Hypothesis(word, score)
    return sorted(best.values(), key=lambda h: h.score, reverse=True)


class GoogleTrans:
    name = "googletrans"

    def __init__(self) -> None:
        self._languages: frozenset[Language] | None = None

    def languages(self) -> frozenset[Language]:
        if self._languages is None:
            self._languages = frozenset(
                Language.parse(code, name.title())
                for code, name in _language_table().items()
                if len(code) == 2
            )
        return self._languages

    def route(self, src: Language, dst: Language) -> list[Pair] | None:
        """[] if src == dst, the pair itself if Google supports both, else None."""
        if src == dst:
            return []
        known = self.languages()
        return [Pair(src, dst)] if src in known and dst in known else None

    def load(self, src: str, dst: str) -> None:
        if self.route(Language.parse(src), Language.parse(dst)) is None:
            raise PairNotInstalled(src, dst)

    def translate(self, text: str, src: str, dst: str, n: int = 1) -> list[Hypothesis]:
        self.load(src, dst)
        if not text.strip():
            return []
        try:
            return asyncio.run(self._translate(text, src, dst, max(1, n)))
        except Exception as e:  # httpx errors, or googletrans's "Unexpected status code"
            raise BackendUnavailable(self.name, f"{type(e).__name__}: {e}") from e

    async def _translate(self, text: str, src: str, dst: str, n: int) -> list[Hypothesis]:
        from googletrans import Translator

        # raise_exception=True: otherwise googletrans silently returns the input text on failure.
        async with Translator(service_urls=[_SERVICE_URL], raise_exception=True,
                              timeout=_TIMEOUT, http2=False) as translator:
            result = await translator.translate(text, dest=dst, src=src)

        alternatives = _dictionary_entries(result.extra_data)
        best = alternatives[0].score if alternatives else 0.0
        hypotheses = [Hypothesis(result.text, best)]  # Google's own pick always leads
        seen = {result.text.casefold()}
        for alt in alternatives:
            if alt.text.casefold() not in seen:
                seen.add(alt.text.casefold())
                hypotheses.append(alt)
        return hypotheses[:n]
