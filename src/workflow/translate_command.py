"""`main.py translate "<query>"`: the main Alfred script filter (keyword + pair + text).

Flow: read settings -> parse the query -> show one of
  - the help row,
  - a pair template ("Translate from 🇩🇪 -> __ (ISO Mode)") while the pair is incomplete,
  - a download row when the model for the pair isn't installed,
  - ranked translations (Tab on a row swaps the pair and carries the word over).
"""
import json

from translate import make_backend
from translate.backends.argos_catalog import ArgosCatalog
from translate.errors import PairNotInstalled
from translate.select import select
from translate.types import Backend, Language, Pair
from workflow.environment import (
    ConfigError, cache_dir, get_chosen_backend_name, get_flag_map, get_quickcode_map,
)
from workflow.parse import parse_command
from workflow.types import (
    CommandHelp, CommandListModels, CommandTryTranslate, InvalidCode, LanguageQuery,
    ParsedLanguage, TranslationRequest, Unfilled,
)

N_HYPOTHESES = 5


def _emit(*items: dict) -> None:
    print(json.dumps({"items": list(items)}))


def _row(title: str, subtitle: str = "", **extra) -> dict:
    return {"title": title, "subtitle": subtitle, "valid": False, **extra}


def _slot(q: LanguageQuery) -> str:
    match q:
        case ParsedLanguage(flag=flag):
            return flag
        case Unfilled():
            return "__"
        case InvalidCode():
            return "❓️"


def _template(req: TranslationRequest) -> str:
    mode = "ISO Mode" if req.iso_mode else "QuickCode"
    return f"Translate from {_slot(req.src)} -> {_slot(req.target)} ({mode})"


def _swapped_token(src: str, dst: str, iso_mode: bool, quickcodes: dict[str, str]) -> str:
    """The pair token for dst -> src, in the mode the user is typing in."""
    if not iso_mode:
        letter_for = {code: letter for letter, code in quickcodes.items()}
        if src in letter_for and dst in letter_for:
            return letter_for[dst] + letter_for[src]
    return f".{dst}{src}"


def _download_row(route: list[Pair], err: PairNotInstalled) -> dict:
    """Row that starts downloading the first missing model on the route.

    Enter sends `from`/`to` to the same download chain the `ntd` pair list uses.
    A pivoted route can need several models; they are fetched one at a time.
    """
    installed = ArgosCatalog(cache_dir()).installed()
    missing = [p for p in route if (p.src.code, p.dst.code) not in installed]
    if not missing:  # the backend refused although every model on the route is installed
        return _row("Translation failed", str(err))

    def name(p: Pair) -> str:
        return f"{p.src.name or p.src.code} → {p.dst.name or p.dst.code}"

    first = missing[0]
    subtitle = "↩ to download"
    if len(missing) > 1:
        rest = ", ".join(name(p) for p in missing[1:])
        subtitle += f"  ·  step 1 of {len(missing)}, then: {rest}"
    return {
        "title": f"{name(first)} isn't installed",
        "subtitle": subtitle,
        "valid": True,
        "variables": {"from": first.src.code, "to": first.dst.code},
        "arg": f"{first.src.code} {first.dst.code}",
    }


def _translate(req: TranslationRequest, backend: Backend, quickcodes: dict[str, str]) -> None:
    template = _template(req)
    src, dst = req.src, req.target

    if isinstance(src, InvalidCode) or isinstance(dst, InvalidCode):
        _emit(_row(template, "Unknown language code"))
        return
    if not (isinstance(src, ParsedLanguage) and isinstance(dst, ParsedLanguage)):
        _emit(_row(template, "Keep typing the language pair"))
        return
    if src.iso_code == dst.iso_code:
        _emit(_row(template, "Pick two different languages"))
        return
    if not req.text:
        _emit(_row(template, "Type the text to translate"))
        return

    s, d = Language.parse(src.iso_code), Language.parse(dst.iso_code)
    route = backend.route(s, d)
    if route is None:
        _emit(_row(template, f"{backend.name} can't translate {s.code} → {d.code}"))
        return

    try:
        hypotheses = backend.translate(req.text, s.code, d.code, n=N_HYPOTHESES)
    except PairNotInstalled as e:
        _emit(_download_row(route, e))
        return

    ranked = select(hypotheses) if hypotheses else []
    if not ranked:
        _emit(_row("No translation returned", template))
        return
    swap = _swapped_token(s.code, d.code, req.iso_mode, quickcodes)
    # No `uid`: Alfred would reorder rows by past use, but these are ranked best-first.
    _emit(*({
        "title": h.text,
        "subtitle": f"{src.flag} -> {dst.flag}",
        "valid": True,
        "arg": h.text,
        "autocomplete": f"{swap} {h.text}",  # Tab = ping-pong: swap the pair, keep the word
        "text": {"copy": h.text, "largetype": h.text},
    } for h in ranked))


def _run(query: str) -> None:
    try:
        backend = make_backend(get_chosen_backend_name(), cache_dir())
    except ValueError as e:  # unknown backend name
        raise ConfigError(str(e)) from e
    quickcodes, flags = get_quickcode_map(), get_flag_map()
    supported = {lang.code for lang in backend.languages()}

    match parse_command(query, quickcodes, flags, supported):
        case CommandHelp():
            _emit(_row("Translate with WordWeave...",
                       "Type a language pair, then the text: “ge hello” or “.deen hello”"))
        case CommandListModels(filter=text):
            from workflow.list_pairs import main as list_pairs
            list_pairs([text])
        case CommandTryTranslate(request=req):
            _translate(req, backend, quickcodes)
        case _:
            _emit(_row("WordWeave: unsupported command"))


def main(argv: list[str]) -> None:
    try:
        _run(" ".join(argv))
    except ConfigError as e:
        _emit(_row("WordWeave: settings problem", str(e)))
    except Exception as e:  # Alfred shows nothing on a crash, so surface it as a row
        _emit(_row("WordWeave: something went wrong", f"{type(e).__name__}: {e}"))
