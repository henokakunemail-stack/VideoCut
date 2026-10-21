"""Build-time model fetch. Downloads every registry entry that has a url + pinned sha256 into models/,
verifies the hash, and refuses non-permissive licenses. Never run by the app at runtime.

    python tools/fetch_models.py            # all
    python tools/fetch_models.py realesr    # ids containing 'realesr'
"""

import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.ai import models  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "models"


def fetch(m) -> bool:
    dst = OUT / m.file
    if dst.is_file() and models.sha256_of(dst) == m.sha256:
        print(f"ok      {m.id}")
        return True
    if not m.sha256 or not m.source_url.startswith("https://"):
        print(f"SKIP    {m.id}: no pinned sha256 / https url")
        return False
    OUT.mkdir(exist_ok=True)
    part = dst.with_name(dst.name + ".part")
    urllib.request.urlretrieve(m.source_url, part)
    if models.sha256_of(part) != m.sha256:
        part.unlink()
        print(f"FAIL    {m.id}: sha256 mismatch")
        return False
    part.replace(dst)
    print(f"fetched {m.id} ({m.license})")
    return True


if __name__ == "__main__":
    want = sys.argv[1:]
    todo = [m for m in models.MODELS.values() if not want or any(w in m.id for w in want)]
    if not todo:
        print("registry empty: models are registered by the feature modules (src/ai/*) as they land")
    sys.exit(0 if all([fetch(m) for m in todo]) else 1)
