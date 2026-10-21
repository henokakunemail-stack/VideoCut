"""
Beat Sync Engine — detects beats from audio and maps clips to them.
Uses librosa if available, falls back to simple energy-based detection.
"""

import os
import subprocess
import tempfile
import math
from typing import List, Optional, Callable
import numpy as np

from src.core.exporter import ffmpeg_exe

try:
    import librosa as _librosa
    _LIBROSA_OK = True
except ImportError:
    _LIBROSA_OK = False


def is_librosa_available() -> bool:
    return _LIBROSA_OK


class BeatSyncEngine:

    @staticmethod
    def detect_beats(
        audio_path: str,
        sensitivity: float = 0.5,
        min_bpm: float = 60.0,
        max_bpm: float = 200.0,
        progress_cb: Optional[Callable[[float], None]] = None,
    ) -> List[float]:
        """Return list of beat timestamps in seconds."""
        if _LIBROSA_OK:
            return BeatSyncEngine._librosa_beats(
                audio_path, sensitivity, min_bpm, max_bpm, progress_cb
            )
        return BeatSyncEngine._energy_beats(
            audio_path, sensitivity, min_bpm, max_bpm, progress_cb
        )

    @staticmethod
    def _librosa_beats(
        audio_path: str,
        sensitivity: float,
        min_bpm: float,
        max_bpm: float,
        progress_cb,
    ) -> List[float]:
        y, sr = _librosa.load(audio_path, sr=22050, mono=True)
        if progress_cb:
            progress_cb(0.3)

        tempo, beat_frames = _librosa.beat.beat_track(
            y=y, sr=sr,
            bpm=None,
            tightness=100.0 - sensitivity * 80.0,
        )
        beat_times = _librosa.frames_to_time(beat_frames, sr=sr).tolist()

        # Filter by BPM bounds
        if len(beat_times) > 1:
            avg_interval = (beat_times[-1] - beat_times[0]) / max(1, len(beat_times) - 1)
            detected_bpm = 60.0 / avg_interval if avg_interval > 0 else 120.0
            if not (min_bpm <= detected_bpm <= max_bpm):
                # Halve or double
                if detected_bpm < min_bpm:
                    beat_times = beat_times[::2]
                elif detected_bpm > max_bpm:
                    mid_times = []
                    for i in range(len(beat_times) - 1):
                        mid_times.append(beat_times[i])
                        mid_times.append((beat_times[i] + beat_times[i + 1]) / 2)
                    beat_times = mid_times

        if progress_cb:
            progress_cb(1.0)
        return beat_times

    @staticmethod
    def _energy_beats(
        audio_path: str,
        sensitivity: float,
        min_bpm: float,
        max_bpm: float,
        progress_cb,
    ) -> List[float]:
        """Simple energy-based beat detection using raw PCM from ffmpeg."""
        with tempfile.NamedTemporaryFile(suffix=".raw", delete=False) as tf:
            raw_path = tf.name

        try:
            cmd = [
                ffmpeg_exe(), "-y", "-i", audio_path,
                "-f", "s16le", "-acodec", "pcm_s16le",
                "-ar", "22050", "-ac", "1", raw_path
            ]
            subprocess.run(cmd, capture_output=True, timeout=120)

            data = np.frombuffer(open(raw_path, "rb").read(), dtype=np.int16).astype(np.float32)
        finally:
            try:
                os.unlink(raw_path)
            except Exception:
                pass

        if len(data) == 0:
            return []

        sr = 22050
        frame_size = 512
        hop = 256

        # Compute energy per frame
        energies = []
        for i in range(0, len(data) - frame_size, hop):
            chunk = data[i:i + frame_size]
            energies.append(float(np.mean(chunk ** 2)))

        energies = np.array(energies)
        if energies.max() > 0:
            energies /= energies.max()

        if progress_cb:
            progress_cb(0.5)

        # Simple thresholding with local mean
        window = int(sr / hop)  # ~1 second window
        beats = []
        last_beat = -1.0
        min_interval = 60.0 / max_bpm
        max_interval = 60.0 / min_bpm

        for i in range(len(energies)):
            lo = max(0, i - window)
            hi = min(len(energies), i + window)
            local_mean = energies[lo:hi].mean()
            threshold = local_mean * (1.0 + (1.0 - sensitivity) * 1.5)

            t = i * hop / sr
            if (energies[i] > threshold and
                    (last_beat < 0 or (t - last_beat) >= min_interval)):
                beats.append(t)
                last_beat = t

        if progress_cb:
            progress_cb(1.0)
        return beats

    @staticmethod
    def map_clips_to_beats(
        beats: List[float],
        clip_count: int,
        video_duration: float,
        strategy: str = "cut_on_beat",
    ) -> List[float]:
        """
        Return a list of cut points (timestamps) for the given number of clips.
        strategy: 'cut_on_beat' | 'cut_every_n_beats' | 'fill_duration'
        """
        if not beats or clip_count <= 0:
            return []

        if strategy == "cut_on_beat":
            # Evenly sample beats
            indices = np.linspace(0, len(beats) - 1, clip_count, dtype=int)
            return [beats[i] for i in indices]

        elif strategy == "cut_every_n_beats":
            n = max(1, len(beats) // max(1, clip_count))
            return [beats[i] for i in range(0, len(beats), n)][:clip_count]

        else:  # fill_duration
            step = video_duration / max(1, clip_count)
            return [i * step for i in range(clip_count)]

    @staticmethod
    def extract_audio_from_video(video_path: str) -> Optional[str]:
        """Extract audio to a temp WAV, return path. Caller must delete."""
        tf = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tf.close()
        cmd = [
            ffmpeg_exe(), "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", "22050", "-ac", "1", tf.name
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=120, check=True)
            return tf.name
        except Exception:
            try:
                os.unlink(tf.name)
            except Exception:
                pass
            return None

    @staticmethod
    def get_bpm(beats: List[float]) -> float:
        """Median-interval BPM from beat times (seconds)."""
        if len(beats) < 2:
            return 0.0
        return 60.0 / float(np.median(np.diff(beats)))


def snap_cuts(clips, beats_ms) -> int:
    """Lay main-track clips back to back and trim each one's end to the nearest beat at or before it.
    Returns number of trimmed cuts. ponytail: only constant-speed forward video/images are trimmed;
    speed-curve/reverse/freeze clips keep their length. Last clip is never trimmed."""
    if not clips or not beats_ms:
        return 0
    t, n = clips[0].timeline_start, 0
    for i, c in enumerate(clips):
        d = c.timeline_end - c.timeline_start
        c.timeline_start, c.timeline_end = t, t + d
        simple = not (c.speed_curve or c.reverse or c.freeze)
        floor = [b for b in beats_ms if c.timeline_start + 200 <= b <= c.timeline_end]
        if i < len(clips) - 1 and simple and floor and floor[-1] < c.timeline_end:
            cut = c.timeline_end - floor[-1]
            if c.source_end:
                c.source_end -= int(round(cut * c.speed))
            c.timeline_end = floor[-1]
            n += 1
        t = c.timeline_end
    return n
