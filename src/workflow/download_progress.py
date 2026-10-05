import json, sys, time

from workflow.environment import cache_dir

STALE_AFTER = 120


def bar(pct, width=20):
    filled = round(width * pct / 100)
    return "▓" * filled + "░" * (width - filled)


def emit(item, rerun=None):
    out = {"items": [item]}
    if rerun:
        out["rerun"] = rerun
    print(json.dumps(out))
    sys.exit(0)


def main(argv: list[str]) -> None:
    state = cache_dir() / "progress.json"

    try:
        s = json.loads(state.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        emit({"title": "No download running",
              "subtitle": "Use the dl keyword to pick a language pair", "valid": False})

    label = s.get("label", "")

    if s.get("error"):
        state.unlink(missing_ok=True)          # so the next attempt starts clean
        emit({"title": f"Failed: {label}", "subtitle": s["error"], "valid": False})

    if s.get("done"):
        state.unlink(missing_ok=True)
        emit({"title": f"{label} installed ✅", "subtitle": bar(100) + "  100%", "valid": False})

    if time.time() - s.get("ts", 0) > STALE_AFTER:
        state.unlink(missing_ok=True)
        emit({"title": f"Download stalled: {label}",
              "subtitle": "No progress for 2 minutes. Check job.log in the workflow cache folder.",
              "valid": False})

    if s.get("phase") == "install":
        emit({"title": f"Installing {label}…", "subtitle": bar(100), "valid": False}, rerun=0.3)

    if s.get("pct") is None:                   # server sent no Content-Length
        frame = "▖▘▝▗"[int(time.time() * 5) % 4]
        emit({"title": f"Downloading {label}…",
              "subtitle": f"{frame}  {s.get('bytes', 0) / 1e6:.1f} MB", "valid": False}, rerun=0.2)

    emit({"title": f"Downloading {label}  {s['pct']}%",
          "subtitle": bar(s["pct"]), "valid": False}, rerun=0.2)
