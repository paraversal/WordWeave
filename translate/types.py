"""Shared types. Keep this module dependency-free (stdlib only)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Protocol

@dataclass(frozen=True, slots=True)
class Language:
    code: str
    name: str = field(default="", compare=False)  # display only; ignored in ==/hash

    @classmethod
    def parse(cls, code: str, name: str = "") -> "Language":
        return cls(code.strip().lower(), name)

    def __str__(self) -> str:
        return self.code


@dataclass(frozen=True, slots=True)
class Pair:
    src: Language
    dst: Language


@dataclass(frozen=True)
class Hypothesis:
    """One candidate translation.

    `score` is a model log-probability-style number. It is only meaningful for
    ranking candidates of the SAME input from the SAME backend: don't compare it
    across inputs or across engines.
    """

    text: str
    score: float | None = None


class Backend(Protocol):
    """What every translation backend offers. A router/fallback layer builds on this."""

    name: str

    def load(self, src: str, dst: str) -> None:
        """Eagerly import and load everything needed for src->dst. Idempotent.

        Raises PairNotInstalled if the backend can't translate this pair.
        """

    def translate(self, text: str, src: str, dst: str, n: int = 1) -> list[Hypothesis]:
        """Return up to `n` ranked hypotheses, best first. Loads lazily if needed."""
        
    def languages(self) -> frozenset[Language]: ...
    def route(self, src: Language, dst: Language) -> list[Pair] | None: ...




