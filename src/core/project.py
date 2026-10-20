"""
Project Management - handles project state, clips, timeline data
"""

import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from enum import Enum


class ClipType(Enum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"
    TEXT = "text"
    STICKER = "sticker"


@dataclass
class TextStyle:
    font_family: str = "Arial"
    font_size: int = 48
    bold: bool = False
    italic: bool = False
    color: str = "#ffffff"
    stroke_color: str = "#000000"
    stroke_width: int = 0
    shadow: bool = False
    background_color: str = "transparent"
    alignment: str = "center"  # left, center, right


@dataclass
class ClipEffect:
    effect_id: str = ""
    name: str = ""
    intensity: float = 1.0
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Clip:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    clip_type: ClipType = ClipType.VIDEO
    source_path: str = ""
    track: int = 0  # 0=main, 1=overlay, 2=audio, etc.

    # Timeline position (in milliseconds)
    timeline_start: int = 0
    timeline_end: int = 5000

    # Source trim (in milliseconds)
    source_start: int = 0
    source_end: int = 5000

    # Transform
    position_x: float = 0.5   # 0.0 - 1.0 (normalized)
    position_y: float = 0.5
    scale_x: float = 1.0
    scale_y: float = 1.0
    rotation: float = 0.0
    opacity: float = 1.0
    flip_h: bool = False
    flip_v: bool = False

    # Color
    brightness: float = 0.0   # -1 to 1
    contrast: float = 0.0
    saturation: float = 0.0
    temperature: float = 0.0
    tint: float = 0.0
    highlight: float = 0.0
    shadow: float = 0.0
    sharpness: float = 0.0
    vignette: float = 0.0
    fade_in: float = 0.0
    fade_out: float = 0.0

    # Audio
    volume: float = 1.0
    muted: bool = False
    audio_fade_in: float = 0.0
    audio_fade_out: float = 0.0

    # Speed
    speed: float = 1.0
    reverse: bool = False

    # Filter
    filter_id: str = ""
    filter_intensity: float = 1.0

    # Effects list
    effects: List[ClipEffect] = field(default_factory=list)

    # Text (for text clips)
    text_content: str = ""
    text_style: TextStyle = field(default_factory=TextStyle)

    # Transition in/out
    transition_in: str = ""
    transition_in_duration: int = 500
    transition_out: str = ""
    transition_out_duration: int = 500

    # Crop
    crop_left: float = 0.0
    crop_right: float = 0.0
    crop_top: float = 0.0
    crop_bottom: float = 0.0

    # Mask
    mask_type: str = ""  # circle, rectangle, star, heart, etc.
    mask_inverted: bool = False
    mask_feather: float = 0.1

    # Beauty / Skin
    skin_smooth: float = 0.0    # 0.0 - 1.0
    whitening: float = 0.0
    noise_reduction: float = 0.0
    skin_tone: float = 0.0      # -1.0 to 1.0
    clarity: float = 0.0
    grain: float = 0.0
    dehaze: float = 0.0

    # Color Grading
    lut_id: str = ""             # bleach_bypass, day_for_night, teal_orange, blockbuster
    lut_strength: float = 1.0

    # Chroma Key
    chroma_key_enabled: bool = False
    chroma_key_hue: float = 60.0      # HSV hue 0-180
    chroma_key_saturation: float = 100.0
    chroma_key_value: float = 100.0
    chroma_key_tolerance: float = 30.0

    # Keyframes — list of {time_ms, property, value}
    keyframes: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def duration(self):
        return self.timeline_end - self.timeline_start

    def to_dict(self):
        d = asdict(self)
        d['clip_type'] = self.clip_type.value
        return d

    @classmethod
    def from_dict(cls, data):
        data['clip_type'] = ClipType(data['clip_type'])
        if 'text_style' in data and isinstance(data['text_style'], dict):
            data['text_style'] = TextStyle(**data['text_style'])
        if 'effects' in data:
            data['effects'] = [ClipEffect(**e) for e in data['effects']]
        return cls(**data)


@dataclass
class AudioTrack:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_path: str = ""
    name: str = ""
    timeline_start: int = 0
    timeline_end: int = 5000
    source_start: int = 0
    source_end: int = 5000
    volume: float = 0.8
    muted: bool = False
    fade_in: float = 0.0
    fade_out: float = 0.0

    @property
    def duration(self):
        return self.timeline_end - self.timeline_start


@dataclass
class ProjectSettings:
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    background_color: str = "#000000"
    duration: int = 0  # milliseconds

    # Export settings
    export_quality: str = "high"   # low, medium, high, ultra
    export_format: str = "mp4"
    export_codec: str = "h264"
    export_bitrate: int = 8000  # kbps


class Project:
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.name = "Untitled Project"
        self.path = ""
        self.settings = ProjectSettings()
        self.clips: List[Clip] = []
        self.audio_tracks: List[AudioTrack] = []
        self.is_modified = False

    def add_clip(self, clip: Clip):
        self.clips.append(clip)
        self.is_modified = True
        self._update_duration()

    def remove_clip(self, clip_id: str):
        self.clips = [c for c in self.clips if c.id != clip_id]
        self.is_modified = True
        self._update_duration()

    def get_clip(self, clip_id: str) -> Optional[Clip]:
        for c in self.clips:
            if c.id == clip_id:
                return c
        return None

    def add_audio_track(self, track: AudioTrack):
        self.audio_tracks.append(track)
        self.is_modified = True

    def remove_audio_track(self, track_id: str):
        self.audio_tracks = [t for t in self.audio_tracks if t.id != track_id]
        self.is_modified = True

    def _update_duration(self):
        if self.clips:
            self.settings.duration = max(c.timeline_end for c in self.clips)
        else:
            self.settings.duration = 0

    def get_clips_at_time(self, time_ms: int) -> List[Clip]:
        return [c for c in self.clips
                if c.timeline_start <= time_ms < c.timeline_end]

    def get_main_track_clips(self) -> List[Clip]:
        return sorted([c for c in self.clips if c.track == 0],
                      key=lambda x: x.timeline_start)

    def get_overlay_clips(self) -> List[Clip]:
        return [c for c in self.clips if c.track > 0 and c.clip_type != ClipType.AUDIO]

    def get_text_clips(self) -> List[Clip]:
        return [c for c in self.clips if c.clip_type == ClipType.TEXT]

    def split_clip(self, clip_id: str, split_time_ms: int) -> Optional[Clip]:
        """Split a clip at a given timeline time, returns the new second half clip."""
        clip = self.get_clip(clip_id)
        if not clip:
            return None
        if split_time_ms <= clip.timeline_start or split_time_ms >= clip.timeline_end:
            return None

        # Calculate source time proportionally
        ratio = (split_time_ms - clip.timeline_start) / clip.duration
        source_split = int(clip.source_start + ratio * (clip.source_end - clip.source_start))

        # Create second half
        import copy
        new_clip = copy.deepcopy(clip)
        new_clip.id = str(uuid.uuid4())
        new_clip.timeline_start = split_time_ms
        new_clip.source_start = source_split

        # Trim first half
        clip.timeline_end = split_time_ms
        clip.source_end = source_split

        self.clips.append(new_clip)
        self.is_modified = True
        return new_clip

    def reorder_clips(self, track: int = 0):
        """Sort main track clips by timeline_start."""
        track_clips = [c for c in self.clips if c.track == track]
        other_clips = [c for c in self.clips if c.track != track]
        track_clips.sort(key=lambda x: x.timeline_start)
        self.clips = track_clips + other_clips

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'settings': asdict(self.settings),
            'clips': [c.to_dict() for c in self.clips],
            'audio_tracks': [asdict(t) for t in self.audio_tracks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Project':
        proj = cls()
        proj.id = data.get('id', proj.id)
        proj.name = data.get('name', proj.name)
        if 'settings' in data:
            proj.settings = ProjectSettings(**data['settings'])
        if 'clips' in data:
            proj.clips = [Clip.from_dict(c) for c in data['clips']]
        if 'audio_tracks' in data:
            proj.audio_tracks = [AudioTrack(**t) for t in data['audio_tracks']]
        return proj

    def save(self, path: str):
        self.path = path
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
        self.is_modified = False

    @classmethod
    def load(cls, path: str) -> 'Project':
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        proj = cls.from_dict(data)
        proj.path = path
        return proj
