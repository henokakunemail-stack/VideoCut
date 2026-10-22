"""Voice FX chain [{name, params}] -> one ffmpeg filter string. Single path for preview mix and export."""

import math

_ROBOT_SR = 48000


def _pitch(p):
    return f"rubberband=pitch={2 ** (float(p.get('semitones', 0)) / 12):.5f}:formant=preserved"


def _robot(p):
    # zero-phase spectrum with a window of one pitch period = classic robotisation
    win = 2 ** round(math.log2(_ROBOT_SR / max(50.0, float(p.get('freq_hz', 100)))))
    win = min(2048, max(128, win))
    return f"aresample={_ROBOT_SR},afftfilt=real='hypot(re,im)':imag='0':win_size={win}"


def _echo(p):
    return f"aecho=0.8:0.9:{max(1, int(p.get('delay_ms', 300)))}:{min(0.95, max(0.0, float(p.get('decay', 0.5)))):.2f}"


def _reverb(p):
    # ponytail: multi-tap echo, not convolution; upgrade: afir with a synthetic impulse response
    room, wet = float(p.get('room_size', 0.5)), float(p.get('wet', 0.4))
    s = 0.4 + 1.6 * room
    taps = [23, 37, 61, 97, 151]
    delays = '|'.join(str(int(t * s)) for t in taps)
    decays = '|'.join(f"{wet * 0.7 / (1 + i * 0.6):.2f}" for i in range(len(taps)))
    return f"aecho=0.85:0.9:{delays}:{decays}"


def _distortion(p):
    d = min(1.0, max(0.0, float(p.get('drive', 0.5))))
    return f"volume={1 + 9 * d:.2f},asoftclip=type=tanh,volume=0.7"


def _chorus(p):
    r = min(5.0, max(0.1, float(p.get('rate_hz', 1.5))))
    wet = min(1.0, max(0.0, float(p.get('wet', 0.5))))
    return f"chorus=0.6:{0.5 + 0.4 * wet:.2f}:50|60:0.4|0.32:{r:.2f}|{r * 0.8:.2f}:2|2.3"


def _highpass(p):
    return f"highpass=f={int(p.get('hz', 300))}"


def _lowpass(p):
    return f"lowpass=f={int(p.get('hz', 3400))}"


def _vibrato(p):
    return f"vibrato=f={float(p.get('hz', 6)):.1f}:d={float(p.get('depth', 0.5)):.2f}"


_FILTERS = dict(pitch=_pitch, robot=_robot, echo=_echo, reverb=_reverb, distortion=_distortion,
                chorus=_chorus, highpass=_highpass, lowpass=_lowpass, vibrato=_vibrato)

PRESETS = {
    'Chipmunk': [('pitch', {'semitones': 6})],
    'Deep': [('pitch', {'semitones': -5})],
    'Monster': [('pitch', {'semitones': -8}), ('echo', {'delay_ms': 120, 'decay': 0.4})],
    'Robot': [('robot', {'freq_hz': 100})],
    'Alien': [('pitch', {'semitones': 3}), ('vibrato', {'hz': 7, 'depth': 0.6})],
    'Megaphone': [('highpass', {'hz': 500}), ('lowpass', {'hz': 3500}), ('distortion', {'drive': 0.4})],
    'Telephone': [('highpass', {'hz': 400}), ('lowpass', {'hz': 3000})],
    'Cave': [('reverb', {'room_size': 0.9, 'wet': 0.7}), ('echo', {'delay_ms': 250, 'decay': 0.4})],
    'Radio': [('highpass', {'hz': 250}), ('lowpass', {'hz': 5000}), ('distortion', {'drive': 0.2})],
}


def chain_filters(audio_fx) -> str:
    """'' when empty. Unknown names are skipped (projects from newer versions)."""
    return ','.join(_FILTERS[fx['name']](fx.get('params') or {}) for fx in audio_fx or [] if fx.get('name') in _FILTERS)
