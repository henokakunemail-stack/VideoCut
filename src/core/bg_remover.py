"""
AI Background Remover — uses rembg if available, falls back to OpenCV GrabCut.
"""

import threading
import numpy as np
import cv2
from typing import Optional, Callable

try:
    from rembg import remove as rembg_remove
    _REMBG_OK = True
except ImportError:
    _REMBG_OK = False


def is_rembg_available() -> bool:
    return _REMBG_OK


_lock = threading.Lock()


class BackgroundRemover:

    @staticmethod
    def remove_background(frame: np.ndarray, method: str = "auto") -> np.ndarray:
        """Return BGRA frame with background set to alpha=0."""
        if method == "auto":
            method = "rembg" if _REMBG_OK else "grabcut"

        if method == "rembg" and _REMBG_OK:
            return BackgroundRemover._rembg_remove(frame)
        elif method == "grabcut":
            return BackgroundRemover._grabcut_remove(frame)
        else:
            return BackgroundRemover._grabcut_remove(frame)

    @staticmethod
    def _rembg_remove(frame: np.ndarray) -> np.ndarray:
        with _lock:
            import io
            from PIL import Image
            pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            buf = io.BytesIO()
            pil_img.save(buf, format="PNG")
            buf.seek(0)
            result_bytes = rembg_remove(buf.read())
            result_pil = Image.open(io.BytesIO(result_bytes)).convert("RGBA")
            result_np = np.array(result_pil)
            # PIL RGBA → OpenCV BGRA
            return cv2.cvtColor(result_np, cv2.COLOR_RGBA2BGRA)

    @staticmethod
    def _grabcut_remove(frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        mask = np.zeros((h, w), np.uint8)
        bgd_model = np.zeros((1, 65), np.float64)
        fgd_model = np.zeros((1, 65), np.float64)

        margin_x = max(5, w // 10)
        margin_y = max(5, h // 10)
        rect = (margin_x, margin_y, w - 2 * margin_x, h - 2 * margin_y)

        try:
            cv2.grabCut(frame, mask, rect, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_RECT)
        except Exception:
            # Fallback: simple center crop mask
            mask[margin_y:h - margin_y, margin_x:w - margin_x] = cv2.GC_FGD

        fg_mask = np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)

        # Smooth edges
        fg_mask = cv2.GaussianBlur(fg_mask, (5, 5), 0)
        _, fg_mask = cv2.threshold(fg_mask, 127, 255, cv2.THRESH_BINARY)

        bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)
        bgra[:, :, 3] = fg_mask
        return bgra

    @staticmethod
    def apply_background(
        frame_bgra: np.ndarray,
        bg_frame: Optional[np.ndarray],
        bg_color: tuple = (0, 177, 64),
        feather: int = 2,
    ) -> np.ndarray:
        """Composite BGRA frame onto a background."""
        h, w = frame_bgra.shape[:2]

        # Build background
        if bg_frame is not None:
            bg = cv2.resize(bg_frame, (w, h))
            if bg.shape[2] == 4:
                bg = cv2.cvtColor(bg, cv2.COLOR_BGRA2BGR)
        else:
            bg = np.full((h, w, 3), bg_color, dtype=np.uint8)

        alpha = frame_bgra[:, :, 3].astype(np.float32) / 255.0

        if feather > 0:
            k = feather * 2 + 1
            alpha = cv2.GaussianBlur(alpha, (k, k), 0)

        alpha3 = np.stack([alpha, alpha, alpha], axis=2)
        fg = frame_bgra[:, :, :3].astype(np.float32)
        result = (fg * alpha3 + bg.astype(np.float32) * (1.0 - alpha3)).astype(np.uint8)
        return result

    @staticmethod
    def batch_process_video(
        input_path: str,
        output_path: str,
        method: str = "auto",
        bg_color: tuple = (0, 0, 0),
        bg_video_path: Optional[str] = None,
        feather: int = 2,
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> bool:
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            return False

        fps    = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total  = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        bg_cap = None
        if bg_video_path:
            bg_cap = cv2.VideoCapture(bg_video_path)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        frame_idx = 0
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                bg_frame = None
                if bg_cap and bg_cap.isOpened():
                    bg_ret, bg_frame = bg_cap.read()
                    if not bg_ret:
                        bg_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        _, bg_frame = bg_cap.read()

                bgra   = BackgroundRemover.remove_background(frame, method)
                result = BackgroundRemover.apply_background(bgra, bg_frame, bg_color, feather)
                out.write(result)

                frame_idx += 1
                if progress_cb and total > 0:
                    progress_cb(frame_idx / total)
        finally:
            cap.release()
            out.release()
            if bg_cap:
                bg_cap.release()

        return True
