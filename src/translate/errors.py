"""Exceptions. Routers should catch these."""

class TranslationError(Exception):
    """Base class for everything translate raises on purpose."""


class PairNotInstalled(TranslationError):
    """The backend has no model installed for this direction (src -> dst)."""

    def __init__(self, src: str, dst: str):
        super().__init__(f"no installed model for {src}->{dst}")
        self.src, self.dst = src, dst


class PairUnavailable(TranslationError):
    """No downloadable package exists for this direction in the package index."""

    def __init__(self, src: str, dst: str):
        super().__init__(f"no downloadable package for {src}->{dst}")
        self.src, self.dst = src, dst


class BackendUnavailable(TranslationError):
    """An online backend could not be reached or rejected the request (offline, rate-limited...)."""

    def __init__(self, backend: str, reason: str):
        super().__init__(f"{backend} unavailable: {reason}")
        self.backend, self.reason = backend, reason
