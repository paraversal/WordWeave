import urllib.request
from pathlib import Path
from argostranslate import package, settings

def download_with_progress(pkg, on_progress=None, chunk_size=1 << 16) -> Path:
    """Stream an AvailablePackage to the downloads dir. on_progress(done, total|None)."""
    filename = package.argospm_package_name(pkg) + ".argosmodel"
    settings.downloads_dir.mkdir(parents=True, exist_ok=True)
    dest = settings.downloads_dir / filename
    if dest.exists():
        return dest

    tmp = dest.with_suffix(dest.suffix + ".part")
    last_err = None
    for link in pkg.links:                     
        try:
            req = urllib.request.Request(link, headers={"User-Agent": "WordWeave/0.1 (+https://github.com/paraversal/WordWeave)"})
            with urllib.request.urlopen(req, timeout=30) as resp, open(tmp, "wb") as f:
                total = int(resp.headers.get("Content-Length") or 0) or None
                done = 0
                while chunk := resp.read(chunk_size):
                    f.write(chunk)
                    done += len(chunk)
                    if on_progress:
                        on_progress(done, total)
            tmp.replace(dest)            
            return dest
        except Exception as e:
            last_err = e
            tmp.unlink(missing_ok=True)
    raise RuntimeError(f"Download failed for {pkg}") from last_err