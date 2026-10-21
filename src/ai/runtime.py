"""ONNX Runtime sessions (cached per thread). DirectML if that build is installed, else CPU."""

import os
import threading

from src.ai.models import resolve

_sessions = {}
_lock = threading.Lock()


def providers():
    import onnxruntime as ort
    have = ort.get_available_providers()
    return [p for p in ("DmlExecutionProvider", "CPUExecutionProvider") if p in have]


def ort_session(model_id: str):
    """Session for a registered model. One per (model, thread): sessions are not shared across workers."""
    key = (model_id, threading.get_ident())
    with _lock:
        s = _sessions.get(key)
        if s is None:
            import onnxruntime as ort
            opts = ort.SessionOptions()
            opts.intra_op_num_threads = max(1, (os.cpu_count() or 2) - 1)
            s = _sessions[key] = ort.InferenceSession(str(resolve(model_id)), opts, providers=providers())
        return s
