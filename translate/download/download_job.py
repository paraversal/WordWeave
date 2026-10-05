"""Background download job. Launched by workflow/start_download.py as:

    python -m translate.download.download_job <state_file> <from> <to>
"""
import json, os, sys, time


def run(state_file: str, frm: str, to: str) -> None:
    from argostranslate import package
    from translate.download.download_dispatch import download_with_progress

    label = f"{frm}→{to}"

    def write_state(**kw):
        state = {"phase": "download", "pct": None, "bytes": 0, "error": None,
                 "done": False, "label": label, "ts": time.time(), **kw}
        with open(state_file + ".tmp", "w") as f:
            json.dump(state, f)
        os.replace(state_file + ".tmp", state_file)

    last = 0.0

    def on_progress(done, total):
        nonlocal last
        now = time.monotonic()
        if now - last < 0.1 and done != total:
            return
        last = now
        write_state(phase="download", bytes=done,
                    pct=int(done * 100 / total) if total else None)

    try:
        write_state(phase="download", pct=0)
        package.update_package_index()
        pkg = next((p for p in package.get_available_packages()
                    if p.from_code == frm and p.to_code == to), None)
        if pkg is None:
            raise RuntimeError(f"No package for {label}")

        path = download_with_progress(pkg, on_progress)
        write_state(phase="install", pct=100)
        package.install_from_path(path)
        write_state(phase="done", pct=100, done=True, bytes=os.path.getsize(path))
    except Exception as e:
        write_state(phase="error", error=str(e))


if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3])
