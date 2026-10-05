"""Backend "lean": Argos models without Argos's translate module.

Why it exists: for a short query, stock Argos spends ~1.9 s mostly on loading
torch (via stanza) to split sentences. The translation itself is three steps:

    tokenize -> ctranslate2 translate_batch -> detokenize

This backend does exactly those steps, with the same tokenizer object, model
files and translate_batch settings that Argos uses internally. The logic is
copied from argostranslate 1.11.0 (`apply_packaged_translation`), so re-run
compare.py after upgrading argostranslate.

Deliberately NOT done (each one is a possible divergence from stock):
  - sentence splitting: multi-sentence text is translated as ONE sequence, which
    these sentence-trained models handle worse the longer it gets
  - paragraph handling: newlines are not preserved
  - result caching

Pivoting: when no direct model is installed, the text is chained through installed
models (e.g. de -> en -> es, at most MAX_HOPS models). Only the best hypothesis is
carried through each intermediate step, and only the last step returns an n-best
list, with that step's scores. Stock Argos pivots too, but may combine
intermediate hypotheses differently, so results can differ from it.

N-best note: for one sentence, hypotheses are a true n-best list from beam
search. Stock Argos builds multi-sentence "hypothesis i" by gluing together each
sentence's i-th hypothesis, so n-best is only really meaningful for words,
phrases and single sentences, in either backend.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from translate.backends.argos_catalog import MAX_HOPS, ArgosCatalog
from translate.errors import PairNotInstalled
from translate.routing import shortest_path
from translate.types import Hypothesis, Language, Pair


@dataclass
class _LoadedPair:
    translator: Any  # ctranslate2.Translator
    tokenizer: Any  # argostranslate tokenizer (SentencePiece or BPE) from the package
    target_prefix: str


class LeanArgos:
    name = "argoslean"

    def __init__(self, catalog: ArgosCatalog) -> None:
        self._ct2: Any = None
        self._package: Any = None
        self._settings: Any = None
        self._pairs: dict[tuple[str, str], _LoadedPair] = {}
        self._routes: dict[tuple[str, str], list[tuple[str, str]]] = {}
        self.catalog = catalog

    def languages(self): return self.catalog.languages()
    def route(self, src, dst): return self.catalog.route(src, dst)

    def _import_dependencies(self) -> None:
        """Import only what translating needs. None of these pull in torch."""
        if self._ct2 is not None:
            return
        import ctranslate2
        import argostranslate.package as package
        from argostranslate import settings
        self._ct2, self._package, self._settings = ctranslate2, package, settings

    def _installed_route(self, src: str, dst: str) -> list[tuple[str, str]]:
        """Shortest chain of INSTALLED models from src to dst (direct model preferred).

        Raises PairNotInstalled if there is none within MAX_HOPS.
        """
        key = (src, dst)
        if key not in self._routes:
            self._import_dependencies()
            installed = [Pair(Language.parse(p.from_code), Language.parse(p.to_code))
                         for p in self._package.get_installed_packages()]
            chain = shortest_path(installed, Language.parse(src), Language.parse(dst), MAX_HOPS)
            if not chain:  # None: unreachable; []: src == dst
                raise PairNotInstalled(src, dst)
            self._routes[key] = [(p.src.code, p.dst.code) for p in chain]
        return self._routes[key]

    def load(self, src: str, dst: str) -> None:
        for hop_src, hop_dst in self._installed_route(src, dst):
            self._load_direct(hop_src, hop_dst)

    def _load_direct(self, src: str, dst: str) -> None:
        key = (src, dst)
        if key in self._pairs:
            return
        self._import_dependencies()

        pkg = next(
            (p for p in self._package.get_installed_packages()
                if p.from_code == src and p.to_code == dst),
            None,
        )
        if pkg is None:
            raise PairNotInstalled(src, dst)

        s = self._settings
        translator = self._ct2.Translator(
            str(pkg.package_path / "model"),
            device=s.device,
            inter_threads=s.inter_threads,
            intra_threads=s.intra_threads,
            compute_type=s.compute_type,
        )
        self._pairs[key] = _LoadedPair(translator, pkg.tokenizer, pkg.target_prefix)

    def translate(self, text: str, src: str, dst: str, n: int = 1) -> list[Hypothesis]:
        hops = self._installed_route(src, dst)
        for hop_src, hop_dst in hops[:-1]:  # intermediate steps: best hypothesis only
            best = self._translate_direct(text, hop_src, hop_dst, 1)
            if not best:
                return []
            text = best[0].text
        last_src, last_dst = hops[-1]
        return self._translate_direct(text, last_src, last_dst, n)

    def _translate_direct(self, text: str, src: str, dst: str, n: int) -> list[Hypothesis]:
        self._load_direct(src, dst)
        pair = self._pairs[(src, dst)]
        s = self._settings
        n = max(1, n)

        result = pair.translator.translate_batch(
            [pair.tokenizer.encode(text)],
            target_prefix=[[pair.target_prefix]] if pair.target_prefix else None,
            replace_unknowns=True,
            max_batch_size=s.batch_size,
            batch_type="tokens",
            beam_size=max(n, s.beam_size),
            num_hypotheses=n,
            length_penalty=0.2,
            return_scores=True,
        )[0]

        hypotheses = []
        for tokens, score in zip(result.hypotheses, result.scores):
            value = pair.tokenizer.decode(tokens)
            if pair.target_prefix and value.startswith(pair.target_prefix):
                value = value[len(pair.target_prefix):]
            if value[:1] == " ":  # the tokenizer adds a leading space; Argos strips it too
                value = value[1:]
            hypotheses.append(Hypothesis(value, score))
        return hypotheses
