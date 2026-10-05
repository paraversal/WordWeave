from dataclasses import dataclass

@dataclass
class ParsedLanguage:
    iso_code: str
    flag: str  # emoji shown in the Alfred row, from the user's language-flag map

@dataclass(frozen=True, slots=True)
class Unfilled:
    pass

@dataclass(frozen=True, slots=True)
class InvalidCode:
    pass

type LanguageQuery = ParsedLanguage | Unfilled | InvalidCode

@dataclass
class TranslationRequest:
    src: LanguageQuery
    target: LanguageQuery
    text: str | None
    iso_mode: bool = False  # True if the pair was typed as `.ende` rather than as quickcodes

# Commands

@dataclass(frozen=True, slots=True)
class CommandHelp:
    pass

@dataclass(frozen=True, slots=True)
class CommandListModels:
    filter: str = ""  # text typed after `#dl`, used to narrow the pair list

@dataclass(frozen=True, slots=True)
class CommandDownloadLanguagePair:
    language_1: LanguageQuery
    language_2: LanguageQuery

@dataclass(frozen=True, slots=True)
class CommandTryTranslate:
    request: TranslationRequest
    

type Command = CommandListModels | CommandDownloadLanguagePair | CommandTryTranslate | CommandHelp

