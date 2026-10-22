"""Model registry. Weights are bundled with the app (models/) or user-supplied; never downloaded
at runtime. tools/fetch_models.py fills models/ at build time and refuses entries without a pinned
sha256 or without a permissive license."""

import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

PERMISSIVE = ("MIT", "BSD", "Apache", "CC0", "ISC")


class ModelMissing(RuntimeError):
    pass


@dataclass(frozen=True)
class Model:
    id: str
    file: str
    sha256: str       # pinned when the entry is added; fetch_models.py verifies it
    license: str
    source_url: str
    size_mb: float = 0.0
    optional: bool = False   # large/High-quality variants: fetched only on request (VIDEOCUT_MODELS=all)


MODELS: dict = {}


def register(m: Model) -> Model:
    if not any(m.license.startswith(p) for p in PERMISSIVE):
        raise ValueError(f"{m.id}: license '{m.license}' is not permissive")
    MODELS[m.id] = m
    return m


def search_dirs():
    env = os.environ.get("VIDEOCUT_MODELS_DIR")
    if env:
        yield Path(env)
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    yield base / "models"
    yield Path(os.environ.get("LOCALAPPDATA", Path.home())) / "VideoCut" / "models"


def sha256_of(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve(model_id: str, verify: bool = False) -> Path:
    m = MODELS.get(model_id)
    if m is None:
        raise ModelMissing(f"unknown model '{model_id}'")
    for d in search_dirs():
        p = d / m.file
        if p.is_file():
            if verify and sha256_of(p) != m.sha256:
                raise ModelMissing(f"{m.file}: sha256 mismatch (corrupt or wrong file)")
            return p
    raise ModelMissing(f"model '{model_id}' not found; place {m.file} in models/ "
                       f"(source: {m.source_url}, license {m.license})")


def available(model_id: str) -> bool:
    try:
        resolve(model_id)
        return True
    except ModelMissing:
        return False
