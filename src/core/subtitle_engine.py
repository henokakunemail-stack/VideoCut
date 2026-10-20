"""
Auto Caption / Subtitle Engine — uses openai-whisper if available,
falls back to a stub that returns empty segments.
"""

import os
import json
import threading
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional, Callable

try:
    import whisper as _whisper
    _WHISPER_OK = True
except ImportError:
    _WHISPER_OK = False


def is_whisper_available() -> bool:
    return _WHISPER_OK


@dataclass
class Subtitle:
    id:    int
    start: float   # seconds
    end:   float   # seconds
    text:  str

    @property
    def duration(self) -> float:
        return self.end - self.start

    def to_srt_block(self) -> str:
        def fmt(t: float) -> str:
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = int(t % 60)
            ms = int((t % 1) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
        return f"{self.id}\n{fmt(self.start)} --> {fmt(self.end)}\n{self.text}\n"

    def to_vtt_block(self) -> str:
        def fmt(t: float) -> str:
            h = int(t // 3600)
            m = int((t % 3600) // 60)
            s = int(t % 60)
            ms = int((t % 1) * 1000)
            return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
        return f"{fmt(self.start)} --> {fmt(self.end)}\n{self.text}\n"


@dataclass
class SubtitleTrack:
    language:  str = "auto"
    subtitles: List[Subtitle] = field(default_factory=list)

    def to_srt(self) -> str:
        return "\n".join(s.to_srt_block() for s in self.subtitles)

    def to_vtt(self) -> str:
        header = "WEBVTT\n\n"
        return header + "\n".join(s.to_vtt_block() for s in self.subtitles)

    def to_json(self) -> str:
        return json.dumps([
            {"id": s.id, "start": s.start, "end": s.end, "text": s.text}
            for s in self.subtitles
        ], indent=2, ensure_ascii=False)

    @staticmethod
    def from_json(data: str) -> "SubtitleTrack":
        track = SubtitleTrack()
        for item in json.loads(data):
            track.subtitles.append(Subtitle(**item))
        return track


_model_lock  = threading.Lock()
_loaded_model = {}


def _get_model(model_name: str = "base"):
    with _model_lock:
        if model_name not in _loaded_model:
            _loaded_model[model_name] = _whisper.load_model(model_name)
        return _loaded_model[model_name]


class SubtitleEngine:
    """Transcribe audio/video to subtitles using Whisper or fallback."""

    @staticmethod
    def transcribe(
        media_path: str,
        language: str = "auto",
        model_name: str = "base",
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> SubtitleTrack:
        if not _WHISPER_OK:
            return SubtitleEngine._stub_transcribe(media_path)

        # Extract audio to temp wav
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            audio_path = tf.name

        try:
            SubtitleEngine._extract_audio(media_path, audio_path)
            if progress_cb:
                progress_cb(0.1)

            model = _get_model(model_name)
            opts = {}
            if language != "auto":
                opts["language"] = language

            result = model.transcribe(audio_path, **opts)

            track = SubtitleTrack(language=result.get("language", ""))
            for i, seg in enumerate(result.get("segments", []), start=1):
                track.subtitles.append(Subtitle(
                    id=i,
                    start=float(seg["start"]),
                    end=float(seg["end"]),
                    text=seg["text"].strip(),
                ))
            if progress_cb:
                progress_cb(1.0)
            return track

        finally:
            try:
                os.unlink(audio_path)
            except Exception:
                pass

    @staticmethod
    def _extract_audio(media_path: str, output_wav: str) -> bool:
        cmd = [
            "ffmpeg", "-y", "-i", media_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "16000", "-ac", "1",
            output_wav
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=300, check=True)
            return True
        except Exception:
            return False

    @staticmethod
    def _stub_transcribe(media_path: str) -> SubtitleTrack:
        """Return empty track when Whisper is not installed."""
        track = SubtitleTrack(language="")
        track.subtitles.append(Subtitle(
            id=1, start=0.0, end=3.0,
            text="[Whisper not installed — pip install openai-whisper]"
        ))
        return track

    @staticmethod
    def save_srt(track: SubtitleTrack, path: str) -> bool:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(track.to_srt())
            return True
        except Exception:
            return False

    @staticmethod
    def save_vtt(track: SubtitleTrack, path: str) -> bool:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(track.to_vtt())
            return True
        except Exception:
            return False

    @staticmethod
    def burn_subtitles(
        video_path: str,
        output_path: str,
        track: SubtitleTrack,
        font_size: int = 24,
        font_color: str = "white",
        outline_color: str = "black",
        position: str = "bottom",
    ) -> bool:
        """Burn subtitles directly into the video using ffmpeg subtitles filter."""
        with tempfile.NamedTemporaryFile(suffix=".srt", delete=False, mode="w",
                                         encoding="utf-8") as tf:
            tf.write(track.to_srt())
            srt_path = tf.name

        try:
            # Position: bottom = MarginV=20, top = MarginV=height-50
            margin = "20" if position == "bottom" else "50"
            style = (
                f"FontSize={font_size},"
                f"PrimaryColour=&H00{font_color[::-1].upper() if font_color.startswith('#') else 'FFFFFF'},"
                f"OutlineColour=&H00{outline_color[::-1].upper() if outline_color.startswith('#') else '000000'},"
                f"Outline=2,MarginV={margin}"
            )
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", f"subtitles={srt_path}:force_style='{style}'",
                "-c:a", "copy",
                output_path
            ]
            subprocess.run(cmd, capture_output=True, timeout=600, check=True)
            return True
        except Exception:
            return False
        finally:
            try:
                os.unlink(srt_path)
            except Exception:
                pass
