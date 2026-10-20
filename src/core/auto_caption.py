"""
Auto Caption / Subtitle Engine — OpenAI Whisper with ffmpeg audio extraction
"""
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from typing import List, Optional

WHISPER_AVAILABLE = False
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    pass


@dataclass
class SubtitleSegment:
    start: float       # seconds
    end: float         # seconds
    text: str
    confidence: float = 1.0


class AutoCaption:
    """Transcribe audio from video file and return subtitle segments."""

    _model_cache: dict = {}

    @classmethod
    def transcribe(cls, video_path: str, model_size: str = "base",
                   language: Optional[str] = None) -> List[SubtitleSegment]:
        """
        Transcribe video audio → subtitle segments.
        model_size: tiny | base | small | medium | large
        language: ISO code or None for auto-detect
        """
        if not WHISPER_AVAILABLE:
            return cls._mock_segments(video_path)

        # Extract audio to temp WAV
        audio_path = cls._extract_audio(video_path)
        if audio_path is None:
            return []

        try:
            model = cls._get_model(model_size)
            opts = {"task": "transcribe", "verbose": False}
            if language:
                opts["language"] = language
            result = model.transcribe(audio_path, **opts)
            segments = []
            for seg in result.get("segments", []):
                segments.append(SubtitleSegment(
                    start=float(seg["start"]),
                    end=float(seg["end"]),
                    text=seg["text"].strip(),
                    confidence=float(seg.get("no_speech_prob", 0.0)),
                ))
            return segments
        finally:
            try:
                os.remove(audio_path)
            except Exception:
                pass

    @classmethod
    def _get_model(cls, size: str):
        if size not in cls._model_cache:
            cls._model_cache[size] = whisper.load_model(size)
        return cls._model_cache[size]

    @staticmethod
    def _extract_audio(video_path: str) -> Optional[str]:
        """Extract audio to temp WAV using ffmpeg."""
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-ac", "1", "-ar", "16000",
            "-vn", tmp.name,
            "-loglevel", "error"
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=120)
            return tmp.name
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            # Try OpenCV audio extract (cv2 can't do audio — fallback fails silently)
            try:
                os.remove(tmp.name)
            except Exception:
                pass
            return None

    @staticmethod
    def _mock_segments(video_path: str) -> List[SubtitleSegment]:
        """Placeholder segments when whisper not available."""
        return [
            SubtitleSegment(0.0, 3.0, "[Whisper not installed]"),
            SubtitleSegment(3.0, 6.0, "pip install openai-whisper"),
            SubtitleSegment(6.0, 9.0, "to enable auto captions"),
        ]

    @staticmethod
    def to_srt(segments: List[SubtitleSegment]) -> str:
        """Export segments to SRT format string."""
        lines = []
        for i, seg in enumerate(segments, 1):
            start = _fmt_time(seg.start)
            end   = _fmt_time(seg.end)
            lines.append(f"{i}\n{start} --> {end}\n{seg.text}\n")
        return "\n".join(lines)

    @staticmethod
    def to_vtt(segments: List[SubtitleSegment]) -> str:
        """Export segments to WebVTT format string."""
        lines = ["WEBVTT\n"]
        for seg in segments:
            start = _fmt_time(seg.start, vtt=True)
            end   = _fmt_time(seg.end,   vtt=True)
            lines.append(f"{start} --> {end}\n{seg.text}\n")
        return "\n".join(lines)

    @staticmethod
    def is_available() -> bool:
        return WHISPER_AVAILABLE


def _fmt_time(seconds: float, vtt: bool = False) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    sep = "." if vtt else ","
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"
