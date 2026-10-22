"""
Shared render pipeline. Preview and export both call compose_frame, so every
filter/LUT/mask/effect/transition/keyframe behaves the same in both.
"""

import copy
import math

import cv2
import numpy as np
from src.core.video_player import FrameProcessor as FP
from src.core.transitions import transition_frame
from src.core import grading


def _fx_ken_burns(f, p, progress):
    return FP.apply_ken_burns(f, progress, p.get('start_scale', 1.0), p.get('end_scale', 1.3),
                              p.get('start_x', .5), p.get('start_y', .5),
                              p.get('end_x', .5), p.get('end_y', .5))


# effect_id -> fn(frame, params, progress). Ids match EffectsPanel.effect_params_changed names.
EFFECTS = {
    'motion_blur': lambda f, p, t: FP.apply_motion_blur(f, p.get('angle', 0), p.get('strength', 15)),
    'zoom_blur': lambda f, p, t: FP.apply_zoom_blur(f, p.get('strength', .5), p.get('center_x', .5), p.get('center_y', .5)),
    'radial_blur': lambda f, p, t: FP.apply_radial_blur(f, p.get('strength', .5)),
    'ken_burns': _fx_ken_burns,
    'tilt_shift': lambda f, p, t: FP.apply_tilt_shift(f, p.get('focus_y', .5), p.get('blur_amount', 15), p.get('fade_range', .3)),
    'glitch_rgb': lambda f, p, t: FP.apply_glitch_rgb(f, p.get('intensity', .5)),
    'vhs_wobble': lambda f, p, t: FP.apply_vhs_wobble(f, p.get('intensity', .5)),
    'chromatic_aberration': lambda f, p, t: FP.apply_chromatic_aberration(f, p.get('amount', .5)),
}


from src.core import fx_motion
EFFECTS.update({k: v[0] for k, v in fx_motion.FX.items()})
# media-panel effect card id -> (effect id, default params); cards missing here are shown disabled
CARD_EFFECTS = {k: (k, dict(v[1])) for k, v in fx_motion.FX.items()}
CARD_EFFECTS.update({
    'glitch': ('glitch_rgb', {'intensity': .5}), 'vhs': ('vhs_wobble', {'intensity': .5}),
    'chromatic': ('chromatic_aberration', {'amount': .5}),
    'shake': ('camera_shake', dict(fx_motion.FX['camera_shake'][1])),
})


def set_effect(clip, effect_id: str, params: dict):
    """Add/replace effect on clip. params['enabled']==False removes it."""
    clip.effects = [e for e in clip.effects if e.effect_id != effect_id]
    if params.get('enabled', True) and effect_id in EFFECTS:
        from src.core.project import ClipEffect
        clip.effects.append(ClipEffect(effect_id=effect_id, name=effect_id, params=dict(params)))


def source_time(clip, time_ms: int) -> int:
    """Timeline time -> source media time (ms), honouring speed, curve, reverse, freeze."""
    from src.core import timemap
    return int(timemap.source_ms(clip, time_ms))


def fetch_clip_frame(readers: dict, clip, time_ms: int, fast: bool = False):
    """Raw source frame (RGB/RGBA) for a clip at timeline time. Shared by preview and export.
    readers: path -> reader cache owned by the caller. fast=True skips slow interpolation.
    A fresh baked matte (ai.matting) rides along as the alpha channel."""
    f = _source_frame(readers, clip, time_ms, fast)
    if f is not None and clip.ai and 'matte' in clip.ai:
        from src.ai import matting
        if matting.matte_status(clip) == 'ok':
            a = matting.read_matte(readers, clip, source_time(clip, time_ms), f.shape)
            if a is not None:
                if f.shape[2] == 4:
                    a = a * (f[..., 3].astype(np.float32) / 255.0)
                f = np.dstack([f[..., :3], (a * 255 + .5).astype(np.uint8)])
    return f

def _source_frame(readers: dict, clip, time_ms: int, fast: bool = False):
    from src.core.project import ClipType
    from src.core.video_player import VideoReader, ImageReader
    path = clip.source_path
    if clip.clip_type in (ClipType.IMAGE, ClipType.STICKER):
        if path not in readers:
            readers[path] = ImageReader(path)
        return readers[path].read_frame()
    if clip.clip_type != ClipType.VIDEO:
        return None
    if path not in readers:
        r = VideoReader(path)
        readers[path] = r if r.is_valid() else None
    r = readers[path]
    if r is None:
        return None
    from src.core import timemap
    ms = timemap.source_ms(clip, time_ms)
    mode = getattr(clip, 'frame_mode', 'none')
    if mode == 'none' or clip.freeze:
        return r.read_frame(ms)
    pos = ms / 1000.0 * r.fps
    n = int(pos + 1e-6)
    a = pos - n
    f0 = r.read_index(n)
    if f0 is None or a < 0.02 or n + 1 >= r.total_frames:
        return None if f0 is None else f0.copy()
    f1 = r.read_index(n + 1)
    if f1 is None:
        return f0.copy()
    if mode == 'optical_flow' and not fast:
        try:
            from src.core.interp import interpolate
            return interpolate(f0, f1, a, key=(path, n))
        except ImportError:
            pass
    return cv2.addWeighted(f0, 1 - a, f1, a, 0)


def text_infos_at(project, time_ms: int):
    from src.core.project import ClipType
    out = []
    for tc in project.get_clips_at_time(time_ms):
        if tc.clip_type != ClipType.TEXT:
            continue
        s = tc.text_style
        out.append({
            'content': tc.text_content, 'pos_x': tc.position_x, 'pos_y': tc.position_y,
            'style': {'font_family': s.font_family, 'font_size': s.font_size, 'bold': s.bold,
                      'italic': s.italic, 'color': s.color, 'stroke_color': s.stroke_color,
                      'stroke_width': s.stroke_width, 'shadow': s.shadow},
        })
    return out


# ── keyframes + fades ─────────────────────────────────────────────────────────

def effective_clip(clip, time_ms: int):
    """Clip copy with keyframes and fade in/out baked into its fields at time_ms.
    Keyframe props (keyframe_engine.ANIMATABLE_PROPS): opacity %, scale x, rotation deg,
    pos_x/pos_y offset (1.0 = half canvas), brightness/contrast/saturation %, blur sigma.
    Returns (clip_or_copy, extra) where extra holds non-field values (blur)."""
    from src.core.keyframe_engine import KeyframeTrack
    t = (time_ms - clip.timeline_start) / 1000.0
    props = {}
    kfs = [k for k in clip.keyframes if 'props' in k]  # ignore legacy {time_ms, property, value}
    if kfs:
        props = KeyframeTrack.from_dict({'keyframes': kfs}).get_props_at(t)
    fade = 1.0
    if clip.fade_in > 0:
        fade = min(fade, t / clip.fade_in)
    if clip.fade_out > 0:
        fade = min(fade, (clip.duration / 1000.0 - t) / clip.fade_out)
    fade = max(0.0, min(1.0, fade))
    if not props and fade == 1.0:
        return clip, {}
    e = copy.copy(clip)
    e.opacity = clip.opacity * fade * props.get('opacity', 100.0) / 100.0
    s = props.get('scale', 1.0)
    e.scale_x, e.scale_y = clip.scale_x * s, clip.scale_y * s
    e.rotation = clip.rotation + props.get('rotation', 0.0)
    e.position_x = clip.position_x + props.get('pos_x', 0.0) * 0.5
    e.position_y = clip.position_y + props.get('pos_y', 0.0) * 0.5
    e.brightness = clip.brightness + props.get('brightness', 0.0) / 100.0
    e.contrast = clip.contrast + props.get('contrast', 0.0) / 100.0
    e.saturation = clip.saturation + props.get('saturation', 0.0) / 100.0
    return e, {'blur': props.get('blur', 0.0)}


# -- background replacement: the matte is baked by ai.matting; Clip.remove_background/background_path are legacy and ignored --

_bg_meta = {}   # path -> (synthetic Clip, duration_ms)

def _hex_rgb(c):
    c = c.lstrip('#')
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4)) if len(c) == 6 else (0, 255, 0)

def _bg_frame(get_frame, style, clip, time_ms):
    """Replacement-background frame (image, or video looped by modulo) for matte mode 'media'; None if unusable."""
    from src.core.project import Clip, ClipType
    p = style.get('path')
    if not p:
        return None
    if p not in _bg_meta:
        isv = p.lower().endswith(('.mp4', '.mov', '.mkv', '.avi', '.webm'))
        dur = 1000
        if isv:
            cap = cv2.VideoCapture(p)
            dur = max(1, int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / (cap.get(cv2.CAP_PROP_FPS) or 30) * 1000))
            cap.release()
        _bg_meta[p] = (Clip(clip_type=ClipType.VIDEO if isv else ClipType.IMAGE, source_path=p,
                            timeline_end=dur, source_end=dur), dur)
    bc, dur = _bg_meta[p]
    return get_frame(bc, (time_ms - clip.timeline_start) % dur)

def _cover(img, w, h):
    k = max(w / img.shape[1], h / img.shape[0])
    img = cv2.resize(img, (max(w, int(img.shape[1] * k + .5)), max(h, int(img.shape[0] * k + .5))))
    y, x = (img.shape[0] - h) // 2, (img.shape[1] - w) // 2
    return img[y:y + h, x:x + w]

# ── per-clip layer ────────────────────────────────────────────────────────────

def _layer(clip, frame, time_ms, extra=None):
    """Apply every per-clip operation. clip is already effective_clip(). frame is RGB or RGBA
    uint8. Returns (rgb uint8, alpha float32 HxW or None). Opacity is folded into alpha."""
    if frame is None:
        return None, None
    progress = (time_ms - clip.timeline_start) / max(1, clip.duration)

    st = clip.stabilize
    if st and st.get('transforms') and st.get('path') == clip.source_path:
        from src.core import stabilize, timemap
        frame = stabilize.apply(frame, st, timemap.source_ms(clip, time_ms))

    frame = FP.apply_flip(frame, clip.flip_h, clip.flip_v)
    frame = FP.apply_crop(frame, clip.crop_left, clip.crop_right, clip.crop_top, clip.crop_bottom)
    alpha = None
    if frame.shape[2] == 4:
        alpha = frame[..., 3].astype(np.float32) / 255.0
        frame = np.ascontiguousarray(frame[..., :3])

    frame = FP.apply_filter(frame, clip.filter_id, clip.filter_intensity)

    if clip.lut_id:
        graded = grading.apply_named_lut(frame, clip.lut_id)
        s = max(0.0, min(1.0, clip.lut_strength))
        frame = graded if s >= 1.0 else cv2.addWeighted(frame, 1 - s, graded, s, 0)

    cc = copy.copy(clip)
    cc.opacity = 1.0  # opacity is alpha here, not darkening
    frame = FP.apply_color_correction(frame, cc)
    frame = grading.apply_grading(frame, clip)

    for e in clip.effects:
        fn = EFFECTS.get(e.effect_id)
        if fn:
            frame = fn(frame, {**e.params, '_t': time_ms / 1000.0}, progress)

    blur = (extra or {}).get('blur', 0.0)
    if blur > 0.1:
        frame = cv2.GaussianBlur(frame, (0, 0), blur)

    style = None
    if alpha is not None and clip.ai and 'matte' in clip.ai:
        from src.ai import matting
        style = matting.matte_style(clip)
    if style:
        if style['feather'] > 0:
            alpha = cv2.GaussianBlur(alpha, (0, 0), style['feather'] / 2.0)
        bg = None
        if style['mode'] == 'color':
            bg = np.empty_like(frame)
            bg[:] = _hex_rgb(style['color'])
        elif style['mode'] == 'media' and (extra or {}).get('bg') is not None:
            bg = _cover(extra['bg'][..., :3], frame.shape[1], frame.shape[0])
        if bg is not None:
            a3 = alpha[..., None]
            frame = (frame * a3 + bg * (1 - a3) + .5).astype(np.uint8)
            alpha = None

    if clip.chroma_key_enabled:
        rgba = FP.apply_chroma_key(frame, (clip.chroma_key_hue, clip.chroma_key_saturation,
                                           clip.chroma_key_value), clip.chroma_key_tolerance)
        k = rgba[..., 3].astype(np.float32) / 255.0
        alpha = k if alpha is None else alpha * k

    if clip.mask_type:
        h, w = frame.shape[:2]
        m = FP.mask_alpha(h, w, clip.mask_type, clip.mask_feather, clip.mask_inverted)
        alpha = m if alpha is None else alpha * m

    if clip.opacity < 1.0:
        o = max(0.0, clip.opacity)
        alpha = np.full(frame.shape[:2], o, np.float32) if alpha is None else alpha * o
    return frame, alpha


def render_clip_frame(clip, frame, time_ms: int = 0):
    """Single clip -> RGB uint8 (transparent areas over black). frame may be RGB or RGBA."""
    e, extra = effective_clip(clip, time_ms)
    rgb, alpha = _layer(e, frame, time_ms, extra)
    if rgb is None:
        return None
    return rgb if alpha is None else (rgb * alpha[..., None]).astype(np.uint8)


# ── placement on the canvas ───────────────────────────────────────────────────

def _place(rgb, alpha, clip, size, frac):
    """Fit rgb inside frac*canvas, then apply clip scale/rotation/position.
    Returns (premultiplied rgb canvas uint8, alpha canvas float32 HxW)."""
    W, H = size
    lh, lw = rgb.shape[:2]
    f = min(W * frac / lw, H * frac / lh)
    prem = rgb if alpha is None else (rgb * alpha[..., None]).astype(np.uint8)
    a8 = (np.full((lh, lw), 255, np.uint8) if alpha is None else (alpha * 255).astype(np.uint8))

    identity = (frac == 1.0 and abs(clip.scale_x - 1) < 1e-6 and abs(clip.scale_y - 1) < 1e-6
                and abs(clip.rotation) < 1e-6 and abs(clip.position_x - .5) < 1e-6
                and abs(clip.position_y - .5) < 1e-6)
    if identity:
        nw, nh = min(W, max(1, round(lw * f))), min(H, max(1, round(lh * f)))
        x, y = (W - nw) // 2, (H - nh) // 2
        out = np.zeros((H, W, 3), np.uint8)
        oa = np.zeros((H, W), np.float32)
        out[y:y + nh, x:x + nw] = cv2.resize(prem, (nw, nh))
        oa[y:y + nh, x:x + nw] = cv2.resize(a8, (nw, nh)).astype(np.float32) / 255.0
        return out, oa

    th = math.radians(clip.rotation)
    c, s = math.cos(th), math.sin(th)
    sx, sy = f * clip.scale_x, f * clip.scale_y
    px, py = clip.position_x * W, clip.position_y * H
    M = np.array([[c * sx, -s * sy, px - (c * sx * lw / 2 - s * sy * lh / 2)],
                  [s * sx, c * sy, py - (s * sx * lw / 2 + c * sy * lh / 2)]], np.float32)
    src = np.dstack([prem, a8])
    dst = cv2.warpAffine(src, M, (W, H), flags=cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    return np.ascontiguousarray(dst[..., :3]), dst[..., 3].astype(np.float32) / 255.0


def _clip_canvas(clip, get_frame, time_ms, size, frac):
    e, extra = effective_clip(clip, time_ms)
    if clip.ai and 'matte' in clip.ai:
        from src.ai import matting
        st = matting.matte_style(clip)
        if st and st['mode'] == 'media':
            extra = {**extra, 'bg': _bg_frame(get_frame, st, clip, time_ms)}
    rgb, alpha = _layer(e, get_frame(clip, time_ms), time_ms, extra)
    if rgb is None:
        return None
    return _place(rgb, alpha, e, size, frac)


def _visual_types():
    from src.core.project import ClipType
    return (ClipType.VIDEO, ClipType.IMAGE, ClipType.STICKER)


def compose_frame(project, time_ms: int, get_frame, size=None, cache=None):
    """Main track (with transitions) + overlays -> RGB frame of `size` (default: project size).
    get_frame(clip, time_ms) returns the raw source frame (RGB or RGBA).
    cache: optional dict reused across calls to keep frozen transition frames."""
    from src.core.project import ClipType
    s = project.settings
    size = size or (s.width, s.height)
    W, H = size
    clips = project.get_clips_at_time(time_ms)
    main_types = (ClipType.VIDEO, ClipType.IMAGE)

    base = np.zeros((H, W, 3), np.uint8)
    for clip in sorted((c for c in clips if c.track == 0 and c.clip_type in main_types),
                       key=lambda c: c.timeline_start):
        placed = _clip_canvas(clip, get_frame, time_ms, size, 1.0)
        if placed is None:
            continue
        base = placed[0]
        base = _with_transition(project, clip, base, time_ms, get_frame, size, cache)
        break

    vis = _visual_types()
    for ov in sorted((c for c in clips if c.track > 0 and c.clip_type in vis),
                     key=lambda c: (c.track, c.timeline_start)):
        placed = _clip_canvas(ov, get_frame, time_ms, size, 0.5)
        if placed is None:
            continue
        prem, a = placed
        base = (prem + base * (1.0 - a[..., None])).astype(np.uint8)
    return base


def _with_transition(project, clip, base, time_ms, get_frame, size, cache):
    """Blend frozen last frame of the previous main-track clip into `base` during the
    first transition_in_duration of `clip` (ponytail: no timeline overlap; freeze frame)."""
    from src.core.project import ClipType
    prev = max((c for c in project.clips
                if c.track == 0 and c is not clip and c.clip_type in (ClipType.VIDEO, ClipType.IMAGE)
                and abs(c.timeline_end - clip.timeline_start) <= 50),
               key=lambda c: c.timeline_end, default=None)
    tid, dur = clip.transition_in, clip.transition_in_duration
    if not tid and prev is not None and prev.transition_out:
        tid, dur = prev.transition_out, prev.transition_out_duration
    dur = min(dur, clip.duration)
    off = time_ms - clip.timeline_start
    if not tid or dur <= 0 or not (0 <= off < dur):
        return base
    key = (prev.id if prev else None, size)
    out = cache.get(key) if cache is not None else None
    if out is None:
        out = np.zeros_like(base)
        if prev is not None:
            placed = _clip_canvas(prev, get_frame, prev.timeline_end - 1, size, 1.0)
            if placed is not None:
                out = placed[0]
        if cache is not None:
            cache[key] = out
    return transition_frame(tid, out, base, off / dur)
