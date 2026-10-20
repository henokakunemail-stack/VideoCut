"""
Audio FX Panel — Pitch shift, robot voice, echo, reverb, distortion, chorus
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QGroupBox, QCheckBox, QComboBox, QScrollArea,
)
from PyQt6.QtCore import Qt, pyqtSignal

_BTN = ("QPushButton{background:#333;color:#ccc;border:1px solid #555;"
        "border-radius:4px;padding:4px 10px;}"
        "QPushButton:hover{background:#fe2c55;color:white;border-color:#fe2c55;}")
_GRP = ("QGroupBox{color:#aaa;font-size:11px;border:1px solid #333;"
        "border-radius:6px;margin-top:8px;padding-top:6px;}")
_LBL = "color:#aaa;font-size:11px;background:transparent;"


def _row(layout, label: str, mn: int, mx: int, default: int,
         on_change, unit: str = "") -> QSlider:
    r = QHBoxLayout()
    lb = QLabel(label)
    lb.setFixedWidth(90)
    lb.setStyleSheet(_LBL)
    r.addWidget(lb)
    sl = QSlider(Qt.Orientation.Horizontal)
    sl.setRange(mn, mx)
    sl.setValue(default)
    r.addWidget(sl, 1)
    vl = QLabel(f"{default}{unit}")
    vl.setFixedWidth(40)
    vl.setStyleSheet(_LBL)

    def _u(v):
        vl.setText(f"{v}{unit}")
        on_change(v)

    sl.valueChanged.connect(_u)
    r.addWidget(vl)
    layout.addLayout(r)
    return sl


class AudioFxPanel(QWidget):
    """Audio effects control panel."""

    fx_chain_changed = pyqtSignal(list)   # emits list of (name, params)

    def __init__(self, parent=None):
        super().__init__(parent)
        # State
        self._pitch      = 0
        self._robot_en   = False
        self._robot_freq = 100
        self._echo_en    = False
        self._echo_delay = 300
        self._echo_decay = 50
        self._reverb_en  = False
        self._reverb_room = 50
        self._reverb_wet  = 40
        self._dist_en    = False
        self._dist_drive = 50
        self._chorus_en  = False
        self._chorus_rate = 15
        self._chorus_wet  = 50
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;}")

        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        # ── Pitch Shift ──────────────────────────────────────────────────────
        pitch_grp = QGroupBox("Pitch Shift")
        pitch_grp.setStyleSheet(_GRP)
        pl = QVBoxLayout(pitch_grp)
        _row(pl, "Semitones", -12, 12, 0, self._set_pitch, " st")
        presets_row = QHBoxLayout()
        for label, val in [("-12", -12), ("-5", -5), ("0", 0), ("+5", 5), ("+12", 12)]:
            b = QPushButton(label)
            b.setFixedHeight(24)
            b.setStyleSheet(_BTN)
            b.clicked.connect(lambda _, v=val: self._set_pitch_preset(v))
            presets_row.addWidget(b)
        pl.addLayout(presets_row)
        lay.addWidget(pitch_grp)

        # ── Robot Voice ──────────────────────────────────────────────────────
        robot_grp = QGroupBox("Robot Voice")
        robot_grp.setStyleSheet(_GRP)
        rl = QVBoxLayout(robot_grp)
        self._robot_cb = QCheckBox("Enable Robot Voice")
        self._robot_cb.setStyleSheet("color:white;")
        self._robot_cb.toggled.connect(self._set_robot_en)
        rl.addWidget(self._robot_cb)
        _row(rl, "Frequency", 50, 400, 100, self._set_robot_freq, " Hz")
        lay.addWidget(robot_grp)

        # ── Echo ─────────────────────────────────────────────────────────────
        echo_grp = QGroupBox("Echo")
        echo_grp.setStyleSheet(_GRP)
        el = QVBoxLayout(echo_grp)
        self._echo_cb = QCheckBox("Enable Echo")
        self._echo_cb.setStyleSheet("color:white;")
        self._echo_cb.toggled.connect(self._set_echo_en)
        el.addWidget(self._echo_cb)
        _row(el, "Delay",  50, 1000, 300, self._set_echo_delay, " ms")
        _row(el, "Decay",   0,  100,  50, self._set_echo_decay, "%")
        lay.addWidget(echo_grp)

        # ── Reverb ───────────────────────────────────────────────────────────
        rev_grp = QGroupBox("Reverb")
        rev_grp.setStyleSheet(_GRP)
        rv = QVBoxLayout(rev_grp)
        self._reverb_cb = QCheckBox("Enable Reverb")
        self._reverb_cb.setStyleSheet("color:white;")
        self._reverb_cb.toggled.connect(self._set_reverb_en)
        rv.addWidget(self._reverb_cb)
        _row(rv, "Room Size",  0, 100, 50, self._set_reverb_room, "%")
        _row(rv, "Wet Mix",    0, 100, 40, self._set_reverb_wet,  "%")
        lay.addWidget(rev_grp)

        # ── Distortion ───────────────────────────────────────────────────────
        dist_grp = QGroupBox("Distortion")
        dist_grp.setStyleSheet(_GRP)
        dl = QVBoxLayout(dist_grp)
        self._dist_cb = QCheckBox("Enable Distortion")
        self._dist_cb.setStyleSheet("color:white;")
        self._dist_cb.toggled.connect(self._set_dist_en)
        dl.addWidget(self._dist_cb)
        _row(dl, "Drive", 0, 100, 50, self._set_dist_drive, "%")
        lay.addWidget(dist_grp)

        # ── Chorus ───────────────────────────────────────────────────────────
        chor_grp = QGroupBox("Chorus")
        chor_grp.setStyleSheet(_GRP)
        cl = QVBoxLayout(chor_grp)
        self._chorus_cb = QCheckBox("Enable Chorus")
        self._chorus_cb.setStyleSheet("color:white;")
        self._chorus_cb.toggled.connect(self._set_chorus_en)
        cl.addWidget(self._chorus_cb)
        _row(cl, "Rate",  1,  50, 15, self._set_chorus_rate, " ×0.1Hz")
        _row(cl, "Wet",   0, 100, 50, self._set_chorus_wet,  "%")
        lay.addWidget(chor_grp)

        # Apply button
        apply_btn = QPushButton("▶ Apply FX Chain to Clip")
        apply_btn.setFixedHeight(34)
        apply_btn.setStyleSheet(
            "QPushButton{background:#fe2c55;color:white;border:none;"
            "border-radius:5px;font-size:13px;font-weight:600;}"
            "QPushButton:hover{background:#e0254d;}")
        apply_btn.clicked.connect(self._emit_chain)
        lay.addWidget(apply_btn)

        lay.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)

    # ── Setters ───────────────────────────────────────────────────────────────
    def _set_pitch(self, v):       self._pitch = v;        self._emit_chain()
    def _set_pitch_preset(self, v):
        self._pitch = v
        self._emit_chain()

    def _set_robot_en(self, v):    self._robot_en   = v;   self._emit_chain()
    def _set_robot_freq(self, v):  self._robot_freq = v;   self._emit_chain()
    def _set_echo_en(self, v):     self._echo_en    = v;   self._emit_chain()
    def _set_echo_delay(self, v):  self._echo_delay = v;   self._emit_chain()
    def _set_echo_decay(self, v):  self._echo_decay = v;   self._emit_chain()
    def _set_reverb_en(self, v):   self._reverb_en  = v;   self._emit_chain()
    def _set_reverb_room(self, v): self._reverb_room = v;  self._emit_chain()
    def _set_reverb_wet(self, v):  self._reverb_wet = v;   self._emit_chain()
    def _set_dist_en(self, v):     self._dist_en    = v;   self._emit_chain()
    def _set_dist_drive(self, v):  self._dist_drive = v;   self._emit_chain()
    def _set_chorus_en(self, v):   self._chorus_en  = v;   self._emit_chain()
    def _set_chorus_rate(self, v): self._chorus_rate = v;  self._emit_chain()
    def _set_chorus_wet(self, v):  self._chorus_wet = v;   self._emit_chain()

    def _emit_chain(self):
        chain = []
        if self._pitch != 0:
            chain.append(("pitch", {"semitones": float(self._pitch)}))
        if self._robot_en:
            chain.append(("robot", {"freq_hz": float(self._robot_freq)}))
        if self._echo_en:
            chain.append(("echo", {
                "delay_ms": float(self._echo_delay),
                "decay":    self._echo_decay / 100.0,
            }))
        if self._reverb_en:
            chain.append(("reverb", {
                "room_size": self._reverb_room / 100.0,
                "wet":       self._reverb_wet  / 100.0,
            }))
        if self._dist_en:
            chain.append(("distortion", {"drive": self._dist_drive / 100.0}))
        if self._chorus_en:
            chain.append(("chorus", {
                "rate_hz": self._chorus_rate / 10.0,
                "wet":     self._chorus_wet  / 100.0,
            }))
        self.fx_chain_changed.emit(chain)

    def get_chain(self) -> list:
        chain = []
        if self._pitch != 0:
            chain.append(("pitch", {"semitones": float(self._pitch)}))
        if self._robot_en:
            chain.append(("robot", {"freq_hz": float(self._robot_freq)}))
        if self._echo_en:
            chain.append(("echo", {
                "delay_ms": float(self._echo_delay),
                "decay": self._echo_decay / 100.0,
            }))
        if self._reverb_en:
            chain.append(("reverb", {
                "room_size": self._reverb_room / 100.0,
                "wet": self._reverb_wet / 100.0,
            }))
        if self._dist_en:
            chain.append(("distortion", {"drive": self._dist_drive / 100.0}))
        if self._chorus_en:
            chain.append(("chorus", {
                "rate_hz": self._chorus_rate / 10.0,
                "wet": self._chorus_wet / 100.0,
            }))
        return chain
