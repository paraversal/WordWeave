import json, re

from translate.backends.argos_catalog import ArgosCatalog
from workflow.environment import cache_dir


def match(tok, lang):
    return lang.code.startswith(tok) or lang.name.lower().startswith(tok)


def main(argv: list[str]) -> None:
    catalog = ArgosCatalog(cache_dir())
    installed = catalog.installed()

    query = argv[0] if argv else ""
    tokens = [t for t in re.split(r"[\s>→,]+", query.lower()) if t]

    items = []
    for p in catalog.pairs():
        if len(tokens) >= 1 and not match(tokens[0], p.src): continue
        if len(tokens) >= 2 and not match(tokens[1], p.dst): continue
        done = (p.src.code, p.dst.code) in installed
        items.append({
            "title": f"{p.src.name} → {p.dst.name}",
            "subtitle": f"{p.src.code}→{p.dst.code}  ·  "
                        + ("✅️ already installed" if done else "↩ to download"),
            "valid": not done,
            "variables": {"from": p.src.code, "to": p.dst.code},
            "arg": f"{p.src.code} {p.dst.code}",
        })

    print(json.dumps({"items": items or [{
        "title": "No matching language pair",
        "subtitle": "Try e.g. “en pt” or “english port”",
        "valid": False}]}))
