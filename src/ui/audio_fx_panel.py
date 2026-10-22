"""Voice changer / audio FX panel. Emits [(name, params)]; the chain is rendered by core.audio_chain (ffmpeg)."""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QGroupBox, QCheckBox, QComboBox, QScrollArea,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from src.core.audio_chain import PRESETS

_BTN = ("QPushButton{background:#333;color:#ccc;border:1px solid #555;"
        "border-radius:4px;padding:4px 10px;}"
        "QPushButton:hover{background:#fe2c55;color:white;border-color:#fe2c55;}")
_GRP = ("QGroupBox{color:#aaa;font-size:11px;border:1px solid #333;"
        "border-radius:6px;margin-top:8px;padding-top:6px;}")
_LBL = "color:#aaa;font-size:11px;background:transparent;"

# name -> (title, [(param, label, min, max, default, unit, scale)])  param value = slider / scale
EFFECTS = {
    'pitch':      ("Pitch Shift", [('semitones', "Semitones", -12, 12, 0, " st", 1)]),
    'robot':      ("Robot Voice", [('freq_hz', "Frequency", 50, 400, 100, " Hz", 1)]),
    'echo':       ("Echo", [('delay_ms', "Delay", 50, 1000, 300, " ms", 1), ('decay', "Decay", 0, 100, 50, "%", 100)]),
    'reverb':     ("Reverb", [('room_size', "Room Size", 0, 100, 50, "%", 100), ('wet', "Wet Mix", 0, 100, 40, "%", 100)]),
    'distortion': ("Distortion", [('drive', "Drive", 0, 100, 50, "%", 100)]),
    'chorus':     ("Chorus", [('rate_hz', "Rate", 1, 50, 15, " x0.1Hz", 10), ('wet', "Wet", 0, 100, 50, "%", 100)]),
    # preset-only building blocks (no group): kept so loaded presets round-trip
    'highpass':   (None, [('hz', "", 20, 2000, 300, "", 1)]),
    'lowpass':    (None, [('hz', "", 500, 20000, 3400, "", 1)]),
    'vibrato':    (None, [('hz', "", 1, 20, 6, "", 1), ('depth', "", 0, 100, 50, "", 100)]),
}


class AudioFxPanel(QWidget):
    fx_chain_changed = pyqtSignal(list)   # debounced; list of (name, params)
    audition_requested = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._checks, self._sliders, self._extra = {}, {}, {}   # extra: preset-only blocks currently active
        self._loading = False
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(250)
        self._debounce.timeout.connect(lambda: self.fx_chain_changed.emit(self.get_chain()))
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

        top = QHBoxLayout()
        lb = QLabel("Preset")
        lb.setStyleSheet(_LBL)
        top.addWidget(lb)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["Custom", *PRESETS])
        self.preset_combo.activated.connect(self._on_preset)
        top.addWidget(self.preset_combo, 1)
        reset = QPushButton("Reset")
        reset.setStyleSheet(_BTN)
        reset.clicked.connect(lambda: self.set_chain([]) or self._changed())
        top.addWidget(reset)
        lay.addLayout(top)

        for name, (title, params) in EFFECTS.items():
            if title is None:
                continue
            grp = QGroupBox(title)
            grp.setStyleSheet(_GRP)
            gl = QVBoxLayout(grp)
            if name != 'pitch':
                cb = QCheckBox(f"Enable {title}")
                cb.setStyleSheet("color:white;")
                cb.toggled.connect(self._changed)
                gl.addWidget(cb)
                self._checks[name] = cb
            for pname, label, mn, mx, default, unit, scale in params:
                gl.addLayout(self._slider_row(name, pname, label, mn, mx, default, unit))
            lay.addWidget(grp)

        row = QHBoxLayout()
        self.audition_btn = QPushButton("Audition 8 s")
        self.audition_btn.setStyleSheet(_BTN)
        self.audition_btn.clicked.connect(lambda: self.audition_requested.emit(self.get_chain()))
        row.addWidget(self.audition_btn)
        lay.addLayout(row)
        self.status = QLabel("")
        self.status.setStyleSheet(_LBL)
        lay.addWidget(self.status)
        lay.addStretch()
        scroll.setWidget(container)
        outer.addWidget(scroll)

    def _slider_row(self, name, pname, label, mn, mx, default, unit):
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
        vl.setFixedWidth(60)
        vl.setStyleSheet(_LBL)
        r.addWidget(vl)

        def moved(v):
            vl.setText(f"{v}{unit}")
            self._changed()
        sl.valueChanged.connect(moved)
        self._sliders[(name, pname)] = (sl, default)
        return r

    def _changed(self, *_):
        if self._loading:
            return
        if self.preset_combo.currentIndex() and self.sender() is not self.preset_combo:
            self.preset_combo.setCurrentIndex(0)
        self._debounce.start()

    def _on_preset(self, i):
        if i > 0:
            self.set_chain([{'name': n, 'params': dict(p)} for n, p in PRESETS[self.preset_combo.itemText(i)]])
            self._debounce.start()

    # ---- state <-> chain ----
    def _scale(self, name, pname):
        return next(p[6] for p in EFFECTS[name][1] if p[0] == pname)

    def set_chain(self, chain):
        """chain: [{name, params}] (Clip.audio_fx). Does not emit."""
        self._loading = True
        try:
            for (name, pname), (sl, default) in self._sliders.items():
                sl.setValue(default)
            for cb in self._checks.values():
                cb.setChecked(False)
            self._extra = {}
            for fx in chain:
                name, params = fx['name'], fx.get('params') or {}
                if name not in EFFECTS:
                    continue
                if name in self._checks:
                    self._checks[name].setChecked(True)
                if EFFECTS[name][0] is None:
                    self._extra[name] = params
                    continue
                for pname, v in params.items():
                    if (name, pname) in self._sliders:
                        self._sliders[(name, pname)][0].setValue(round(v * self._scale(name, pname)))
        finally:
            self._loading = False

    def get_chain(self) -> list:
        chain = []
        for name, (title, params) in EFFECTS.items():
            if title is None:
                if name in self._extra:
                    chain.append((name, dict(self._extra[name])))
                continue
            if name == 'pitch':
                if self._sliders[(name, 'semitones')][0].value() == 0:
                    continue
            elif not self._checks[name].isChecked():
                continue
            chain.append((name, {p[0]: float(self._sliders[(name, p[0])][0].value()) / p[6] for p in params}))
        return chain
