"""translate: translation backends behind one small interface.

Importing this package is cheap on purpose (stdlib only). Heavy libraries
(ctranslate2, argostranslate, torch) are imported lazily inside each backend's
load(), so an Alfred script that only needs one backend never pays for the rest.
"""
from translate.backends import BACKENDS, make_backend
from translate.errors import PairNotInstalled, PairUnavailable, TranslationError
from translate.types import Backend, Hypothesis

__all__ = [
    "BACKENDS",
    "Backend",
    "Hypothesis",
    "PairNotInstalled",
    "PairUnavailable",
    "TranslationError",
    "make_backend",
]
