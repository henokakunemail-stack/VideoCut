"""Whole-project audio mixdown for preview. Uses the export's own source list + filtergraph, so what you hear is what you export."""

import hashlib
import os

from src.ai import assets
from src.ai.media import run_ffmpeg
from src.core import timemap
from src.core.exporter import _audio_sources, build_audio_cmd
from src.core.project import ClipType


def _stat(path):
    try:
        st = os.stat(path)
        return path, st.st_mtime_ns, st.st_size
    except OSError:
        return path, 0, 0


def mix_key(project) -> str:
    """Hash of everything that changes the mix; visual-only edits leave it unchanged."""
    parts = [project.settings.duration]
    for c in project.clips:
        if c.clip_type in (ClipType.VIDEO, ClipType.AUDIO) and c.source_path:
            parts.append((_stat(c.audio_source or c.source_path), c.muted, c.volume, c.freeze, c.audio_fx,
                          c.audio_fade_in, c.audio_fade_out, c.timeline_start, c.timeline_end,
                          timemap.audio_segments(c)))
    for t in project.audio_tracks:
        parts.append((_stat(t.source_path), t.muted, t.volume, t.fade_in, t.fade_out, t.timeline_start,
                      t.timeline_end, t.source_start, t.source_end))
    return hashlib.sha1(repr(parts).encode()).hexdigest()[:16]


def render_mix(project, progress=None, cancelled=None):
    """Mixed WAV (48 kHz stereo) for the whole timeline, cached by mix_key. None when nothing is audible."""
    dur_ms = project.settings.duration
    sources = list(_audio_sources(project)) if dur_ms > 0 else []
    audio = build_audio_cmd(sources, dur_ms / 1000, base=0)
    if not audio:
        return None
    d = assets.asset_dir(project)
    out = str(d / f"mix_{mix_key(project)}.wav")
    if os.path.isfile(out):
        return out
    ins, fc, label = audio
    run_ffmpeg([*ins, "-filter_complex", fc, "-map", label, "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "2"],
               out, dur_ms, progress, cancelled)
    for f in d.glob("mix_*.wav"):            # one live mix per project
        if str(f) != out:
            try:
                f.unlink()
            except OSError:
                pass
    return out


def pick_time(audio_ms, last_ms, dt_ms):
    """Playhead for the next tick: the audio clock when it is sane, else free-run by dt."""
    if audio_ms is not None and audio_ms >= last_ms - 200:
        return int(audio_ms)
    return last_ms + dt_ms


def render_audition(clip, chain, secs=8, progress=None, cancelled=None):
    """First `secs` of the clip's trimmed audio through `chain` ([{name, params}]) -> temp WAV."""
    import tempfile
    from src.core.audio_chain import chain_filters
    src = clip.audio_source or clip.source_path
    out = os.path.join(tempfile.gettempdir(), f"videocut_audition_{os.getpid()}.wav")
    a = ["-ss", f"{clip.source_start / 1000:.3f}", "-t", str(secs), "-i", src, "-vn"]
    fx = chain_filters(chain)
    if fx:
        a += ["-af", fx]
    return run_ffmpeg(a + ["-acodec", "pcm_s16le", "-ar", "48000", "-ac", "2"], out, secs * 1000, progress, cancelled)
