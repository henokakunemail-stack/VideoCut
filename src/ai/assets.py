"""Per-project store for baked/derived media (denoised video, mattes, stems, TTS...)."""

import hashlib
import os
import shutil
import tempfile
from pathlib import Path


def asset_dir(project) -> Path:
    """<project>.assets/ next to a saved project, else a temp dir keyed by project id."""
    path = getattr(project, "path", None)
    if path:
        d = Path(path).with_suffix(".assets")
    else:
        d = Path(tempfile.gettempdir()) / "videocut_assets" / project.id
    d.mkdir(parents=True, exist_ok=True)
    return d


def cache_key(path: str, *parts) -> str:
    """Stable key from the source file identity (path, mtime, size) and processing parameters."""
    try:
        st = os.stat(path)
        ident = f"{os.path.abspath(path)}|{st.st_mtime_ns}|{st.st_size}"
    except OSError:
        ident = os.path.abspath(path)
    return hashlib.sha1("|".join([ident, *map(str, parts)]).encode()).hexdigest()[:16]


def _rewrite(obj, old: str, new: str):
    if isinstance(obj, str):
        return new + obj[len(old):] if obj.startswith(old) else obj
    if isinstance(obj, dict):
        return {k: _rewrite(v, old, new) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_rewrite(v, old, new) for v in obj]
    return obj


def relocate(project, new_project_path: str):
    """Save As: copy assets next to the new file and repoint clip paths. Call before project.path changes."""
    old = asset_dir(project)
    new = Path(new_project_path).with_suffix(".assets")
    if old.resolve() == new.resolve():
        return
    if any(old.iterdir()):
        shutil.copytree(old, new, dirs_exist_ok=True)
        for c in project.clips:
            c.ai = _rewrite(c.ai, str(old), str(new))
            c.audio_source = _rewrite(c.audio_source, str(old), str(new))


def prune(project):
    """Delete asset files no clip references."""
    used = set()

    def walk(o):
        if isinstance(o, str):
            used.add(str(Path(o).resolve()))
        elif isinstance(o, dict):
            [walk(v) for v in o.values()]
        elif isinstance(o, list):
            [walk(v) for v in o]
    for c in project.clips:
        walk(c.ai)
        walk(c.audio_source)
    for f in asset_dir(project).iterdir():
        if f.is_file() and str(f.resolve()) not in used:
            f.unlink()
