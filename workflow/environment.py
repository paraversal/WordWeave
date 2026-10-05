"""Everything read from Alfred's environment (workflow settings and variables)."""
import json
import os
from pathlib import Path


class ConfigError(Exception):
    """A workflow setting is missing or malformed. The message is shown to the user."""


def cache_dir() -> Path:
    """The only place the Alfred cache location is read. Everything else calls this."""
    return Path(os.environ.get("alfred_workflow_cache", "/tmp"))


def get_chosen_backend_name() -> str:
    backend = os.environ.get("ww_backend")
    if not backend:
        raise ConfigError("The 'ww_backend' setting is empty. Choose a backend in the workflow settings.")
    return backend


def _json_map(variable: str, label: str, lowercase_values: bool) -> dict[str, str]:
    """Parse a list of single-entry objects, e.g. [{"g": "de"}, {"e": "en"}], into one dict.

    Keys are always lowercased (the parser lowercases what the user types).
    """
    raw = os.environ.get(variable, "")
    if not raw.strip():
        return {}
    try:
        entries = json.loads(raw)
        if not isinstance(entries, list):
            raise ValueError("expected a JSON list")
        merged: dict[str, str] = {}
        for entry in entries:
            if not isinstance(entry, dict):
                raise ValueError("expected a list of objects")
            for key, value in entry.items():
                if not isinstance(value, str):
                    raise ValueError(f"value for {key!r} must be a string")
                value = value.strip()
                merged[key.strip().lower()] = value.lower() if lowercase_values else value
    except (json.JSONDecodeError, ValueError) as e:
        raise ConfigError(f"{label} is not valid: {e}") from e
    return merged


def get_quickcode_map() -> dict[str, str]:
    """Letter -> ISO code, e.g. {"g": "de", "e": "en"}. Letters must be single characters."""
    qmap = _json_map("quickcodemap", "The Quick Code Map", lowercase_values=True)
    bad = [k for k in qmap if len(k) != 1]
    if bad:
        raise ConfigError(f"Quick codes must be a single letter, got: {', '.join(bad)}")
    return qmap


def get_flag_map() -> dict[str, str]:
    """ISO code -> flag emoji, e.g. {"de": "🇩🇪"}."""
    return _json_map("languageflagmap", "The Language-Flag map", lowercase_values=False)
