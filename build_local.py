"""Build the getvout preview entirely from canonical local sources."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "site-source"
OUT = ROOT / "faithful"


def build():
    from analytics_content import apply
    apply()
    if not (SOURCE / "en/index.html").is_file():
        raise SystemExit("Missing site-source/en/index.html")
    files = sorted(path for path in SOURCE.rglob("*") if path.is_file())
    for source in files:
        destination = OUT / source.relative_to(SOURCE)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    manifest = {
        str(path.relative_to(SOURCE)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in files
    }
    (ROOT / "build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Built {len(files)} local files and {len(list(SOURCE.glob('en/**/index.html')))} pages. No network access.")


if __name__ == "__main__":
    build()
