"""Backend "stock": the normal Argos Translate API.

Full-featured (sentence splitting, paragraphs, automatic pivoting through
intermediate languages) but slow to start: `import argostranslate.translate`
pulls in its sentence splitter, which imports stanza and therefore torch
(~1 s), and the first call builds a stanza pipeline on top of that.
"""

from translate.backends.argos_catalog import ArgosCatalog
from translate.errors import PairNotInstalled
from translate.types import Hypothesis


class StockArgos:
    name = "argosstock"

    def __init__(self, catalog: ArgosCatalog) -> None:
        self._translate_module = None
        self._translations: dict[tuple[str, str], object] = {}
        self.catalog = catalog

    def languages(self): return self.catalog.languages()
    def route(self, src, dst): return self.catalog.route(src, dst)

    def load(self, src: str, dst: str) -> None:
        key = (src, dst)
        if key in self._translations:
            return

        if self._translate_module is None:
            import argostranslate.translate as translate_module
            self._translate_module = translate_module

        languages = {lang.code: lang for lang in self._translate_module.get_installed_languages()}
        if src not in languages or dst not in languages:
            raise PairNotInstalled(src, dst)

        translation = languages[src].get_translation(languages[dst])
          # no direct package
        if translation is None:
            raise PairNotInstalled(src, dst)
        self._translations[key] = translation

    def translate(self, text: str, src: str, dst: str, n: int = 1) -> list[Hypothesis]:
        self.load(src, dst)
        hypotheses = self._translations[(src, dst)].hypotheses(text, max(1, n)) #type: ignore
        return [Hypothesis(h.value, h.score) for h in hypotheses]
