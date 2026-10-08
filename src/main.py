"""Single entry point for every Alfred script box: `main.py <command> [args...]`.

Commands are imported lazily, so a command only pays for the modules it uses.
Running through main.py (rather than running files by path) also puts the repo
root on sys.path, which is what makes `import translate` / `import workflow` work.
"""
import sys
from typing import Callable


def _translate(args: list[str]) -> None:
    from workflow.translate_command import main
    main(args)


def _list_pairs(args: list[str]) -> None:
    from workflow.list_pairs import main
    main(args)


def _download(args: list[str]) -> None:
    from workflow.start_download import main
    main(args)


def _progress(args: list[str]) -> None:
    from workflow.download_progress import main
    main(args)


COMMANDS: dict[str, Callable[[list[str]], None]] = {
    "translate": _translate,     # main.py translate <backend> "<query>"
    "list-pairs": _list_pairs,   # main.py list-pairs "<query>"
    "download": _download,       # main.py download <from> <to>
    "progress": _progress,       # main.py progress
}


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in COMMANDS:
        print(f"usage: main.py {{{'|'.join(COMMANDS)}}} [args...]", file=sys.stderr)
        return 2
    COMMANDS[argv[0]](argv[1:])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
