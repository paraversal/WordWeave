import json, subprocess, sys, time
from pathlib import Path

from workflow.environment import cache_dir

REPO = Path(__file__).resolve().parent.parent  # repo root (this file is workflow/start_download.py)


def main(argv: list[str]) -> None:
    frm, to = argv[0], argv[1]
    cache = cache_dir()
    state, log_file = cache / "progress.json", cache / "job.log"

    try:
        s = json.loads(state.read_text())
        if not s["done"] and not s["error"] and time.time() - s["ts"] < 120:
            return  # a download is already running
    except Exception:
        pass

    cache.mkdir(parents=True, exist_ok=True)
    state.write_text(json.dumps({"phase": "download", "pct": 0, "bytes": 0, "error": None,
                                 "done": False, "label": f"{frm}→{to}", "ts": time.time()}))
    log = open(log_file, "w")
    # -m with cwd=REPO puts the repo root on sys.path, so the job can `import translate`
    # (running the file by path would put translate/download/ there instead).
    subprocess.Popen([sys.executable, "-m", "translate.download.download_job", str(state), frm, to],
                     stdout=log, stderr=log, start_new_session=True, cwd=REPO)
