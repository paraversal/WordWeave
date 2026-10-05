"""Turn the text typed after the Alfred keyword into a Command.

Pure functions: no environment, no I/O. Everything they need (quickcode map, flag
map, supported language codes) is passed in, so they are easy to test.

    nt ge hello        quickcode mode: `g`, `e` are letters from the quickcode map
    nt .deen hello     ISO mode: `.` then two 2-letter ISO 639-1 codes
    nt #dl [filter]    list/download language pairs
"""
from collections.abc import Collection, Mapping

from workflow.types import (
    Command, CommandHelp, CommandListModels, CommandTryTranslate,
    InvalidCode, LanguageQuery, ParsedLanguage, TranslationRequest, Unfilled,
)

ISO_CODE_LEN = 2


def _flag(code: str, flags: Mapping[str, str]) -> str:
    return flags.get(code, f"[{code}]")  # no flag configured: show the code instead


def _iso_part(part: str, supported: Collection[str], flags: Mapping[str, str]) -> LanguageQuery:
    if part == "":
        return Unfilled()
    if part in supported:
        return ParsedLanguage(part, _flag(part, flags))
    if len(part) < ISO_CODE_LEN and any(code.startswith(part) for code in supported):
        return Unfilled()  # still typing: some language starts with this
    return InvalidCode()


def _quickcode_part(part: str, quickcodes: Mapping[str, str], flags: Mapping[str, str]) -> LanguageQuery:
    if part == "":
        return Unfilled()
    code = quickcodes.get(part)
    if code is None:
        return InvalidCode()
    return ParsedLanguage(code, _flag(code, flags))


def parse_language_codes(
    user_input: str,
    iso_mode: bool,
    quickcodes: Mapping[str, str],
    flags: Mapping[str, str],
    supported: Collection[str],
) -> tuple[LanguageQuery, LanguageQuery]:
    """Parse the pair token (`.deen` in ISO mode, `ge` in quickcode mode).

    Anything longer than a full pair counts as an invalid second language.
    """
    token = user_input.lower()
    if iso_mode:
        body = token[1:]  # drop the leading "."
        return (_iso_part(body[:ISO_CODE_LEN], supported, flags),
                _iso_part(body[ISO_CODE_LEN:], supported, flags))
    return (_quickcode_part(token[:1], quickcodes, flags),
            _quickcode_part(token[1:], quickcodes, flags))


def parse_command(
    query: str,
    quickcodes: Mapping[str, str],
    flags: Mapping[str, str],
    supported: Collection[str],
) -> Command:
    query = query.strip()
    if query == "":
        return CommandHelp()
    token, _, rest = query.partition(" ")
    rest = rest.strip()

    if token.startswith("#") and "#dl".startswith(token.lower()):
        return CommandListModels(filter=rest)

    iso_mode = token.startswith(".")
    src, dst = parse_language_codes(token, iso_mode, quickcodes, flags, supported)
    return CommandTryTranslate(TranslationRequest(src, dst, rest or None, iso_mode))
