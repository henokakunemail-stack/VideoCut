"""
Keyframe Animation Engine — interpolates clip properties over time.
"""

import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class Keyframe:
    time:   float               # seconds within the clip
    props:  Dict[str, float]    # {property_name: value}
    easing: str = "ease_in_out" # linear|ease_in|ease_out|ease_in_out|bounce|elastic


@dataclass
class KeyframeTrack:
    clip_id:    str
    keyframes:  List[Keyframe] = field(default_factory=list)

    def add(self, keyframe: Keyframe):
        self.keyframes.append(keyframe)
        self.keyframes.sort(key=lambda k: k.time)

    def remove_at(self, time: float, tolerance: float = 0.05):
        self.keyframes = [k for k in self.keyframes
                          if abs(k.time - time) > tolerance]

    def get_props_at(self, t: float) -> Dict[str, float]:
        """Interpolate all properties at time t."""
        if not self.keyframes:
            return {}

        if t <= self.keyframes[0].time:
            return dict(self.keyframes[0].props)

        if t >= self.keyframes[-1].time:
            return dict(self.keyframes[-1].props)

        # Find surrounding keyframes
        for i in range(len(self.keyframes) - 1):
            k0 = self.keyframes[i]
            k1 = self.keyframes[i + 1]
            if k0.time <= t <= k1.time:
                seg_duration = k1.time - k0.time
                if seg_duration <= 0:
                    return dict(k1.props)
                alpha = (t - k0.time) / seg_duration
                alpha = _ease(alpha, k1.easing)
                result = {}
                all_keys = set(k0.props.keys()) | set(k1.props.keys())
                for prop in all_keys:
                    v0 = k0.props.get(prop, 0.0)
                    v1 = k1.props.get(prop, 0.0)
                    result[prop] = v0 + (v1 - v0) * alpha
                return result

        return {}

    def to_dict(self) -> dict:
        return {
            "clip_id": self.clip_id,
            "keyframes": [
                {"time": k.time, "props": k.props, "easing": k.easing}
                for k in self.keyframes
            ]
        }

    @staticmethod
    def from_dict(data: dict) -> "KeyframeTrack":
        track = KeyframeTrack(clip_id=data.get("clip_id", ""))
        for kd in data.get("keyframes", []):
            track.keyframes.append(Keyframe(
                time=kd["time"],
                props=kd["props"],
                easing=kd.get("easing", "ease_in_out"),
            ))
        return track


def _ease(t: float, mode: str) -> float:
    t = max(0.0, min(1.0, t))
    if mode == "linear":
        return t
    elif mode == "ease_in":
        return t * t * t
    elif mode == "ease_out":
        t1 = t - 1.0
        return t1 * t1 * t1 + 1.0
    elif mode == "ease_in_out":
        if t < 0.5:
            return 4.0 * t * t * t
        else:
            t1 = 2.0 * t - 2.0
            return 0.5 * t1 * t1 * t1 + 1.0
    elif mode == "bounce":
        # Bounce ease out
        if t < 1.0 / 2.75:
            return 7.5625 * t * t
        elif t < 2.0 / 2.75:
            t -= 1.5 / 2.75
            return 7.5625 * t * t + 0.75
        elif t < 2.5 / 2.75:
            t -= 2.25 / 2.75
            return 7.5625 * t * t + 0.9375
        else:
            t -= 2.625 / 2.75
            return 7.5625 * t * t + 0.984375
    elif mode == "elastic":
        if t == 0 or t == 1:
            return t
        p = 0.3
        s = p / 4.0
        t -= 1.0
        return -(math.pow(2, 10 * t) * math.sin((t - s) * (2 * math.pi) / p))
    return t


# ── Animatable property definitions ────────────────────────────────────────

ANIMATABLE_PROPS = {
    "opacity":    (0.0, 100.0, 100.0),
    "scale":      (0.1, 5.0,   1.0),
    "rotation":   (-360.0, 360.0, 0.0),
    "pos_x":      (-1.0, 1.0, 0.0),
    "pos_y":      (-1.0, 1.0, 0.0),
    "brightness": (-100.0, 100.0, 0.0),
    "contrast":   (-100.0, 100.0, 0.0),
    "saturation": (-100.0, 100.0, 0.0),
    "blur":       (0.0, 50.0, 0.0),
}


class KeyframeAnimator:
    """Manages all keyframe tracks for a project."""

    def __init__(self):
        self._tracks: Dict[str, KeyframeTrack] = {}

    def get_track(self, clip_id: str) -> KeyframeTrack:
        if clip_id not in self._tracks:
            self._tracks[clip_id] = KeyframeTrack(clip_id=clip_id)
        return self._tracks[clip_id]

    def set_keyframe(self, clip_id: str, time: float,
                     props: Dict[str, float], easing: str = "ease_in_out"):
        track = self.get_track(clip_id)
        # Merge with existing keyframe at same time if close
        for kf in track.keyframes:
            if abs(kf.time - time) < 0.05:
                kf.props.update(props)
                kf.easing = easing
                return
        track.add(Keyframe(time=time, props=dict(props), easing=easing))

    def remove_keyframe(self, clip_id: str, time: float):
        if clip_id in self._tracks:
            self._tracks[clip_id].remove_at(time)

    def get_props_at(self, clip_id: str, t: float) -> Dict[str, float]:
        if clip_id not in self._tracks:
            return {}
        return self._tracks[clip_id].get_props_at(t)

    def has_animation(self, clip_id: str) -> bool:
        return (clip_id in self._tracks and
                len(self._tracks[clip_id].keyframes) > 0)

    def clear_clip(self, clip_id: str):
        if clip_id in self._tracks:
            del self._tracks[clip_id]

    def to_dict(self) -> dict:
        return {cid: t.to_dict() for cid, t in self._tracks.items()}

    def from_dict(self, data: dict):
        self._tracks = {}
        for cid, td in data.items():
            self._tracks[cid] = KeyframeTrack.from_dict(td)
