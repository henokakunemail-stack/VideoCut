"""
Effects Panel — Motion Blur, Ken Burns, Tilt-Shift, Glitch, VHS, Chromatic Aberration
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QTabWidget, QGroupBox, QCheckBox, QComboBox,
    QScrollArea, QGridLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal


def _slider_row(parent_layout, label: str, mn: int, mx: int, default: int,
                on_change, unit: str = "") -> QSlider:
    row = QHBoxLayout()
    lbl = QLabel(label)
    lbl.setFixedWidth(100)
    lbl.setStyleSheet("color:#aaa;font-size:11px;background:transparent;")
    row.addWidget(lbl)

    sl = QSlider(Qt.Orientation.Horizontal)
    sl.setRange(mn, mx)
    sl.setValue(default)
    row.addWidget(sl, 1)

    val_lbl = QLabel(f"{default}{unit}")
    val_lbl.setFixedWidth(36)
    val_lbl.setStyleSheet("color:#ccc;font-size:11px;background:transparent;")

    def _upd(v):
        val_lbl.setText(f"{v}{unit}")
        on_change(v)

    sl.valueChanged.connect(_upd)
    row.addWidget(val_lbl)
    parent_layout.addLayout(row)
    return sl


class EffectsPanel(QWidget):
    """Advanced effects panel: motion blur, Ken Burns, cinematic, glitch."""

    effect_params_changed = pyqtSignal(str, dict)   # (effect_name, params)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabBar::tab{padding:5px 8px;font-size:10px;}")
        self.tabs.addTab(self._build_motion_tab(),    "💨 Motion")
        self.tabs.addTab(self._build_cinematic_tab(), "🎬 Cinematic")
        self.tabs.addTab(self._build_glitch_tab(),    "⚡ Glitch")
        layout.addWidget(self.tabs)

    # ── Tab 1: Motion ─────────────────────────────────────────────────────────

    def _build_motion_tab(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        # Motion Blur
        mb_grp = QGroupBox("Motion Blur")
        mb_grp.setStyleSheet("QGroupBox{color:#aaa;border:1px solid #333;border-radius:6px;"
                              "margin-top:8px;padding-top:6px;}")
        mb_lay = QVBoxLayout(mb_grp)

        self._mb_enabled = QCheckBox("Enable Motion Blur")
        self._mb_enabled.setStyleSheet("color:white;font-size:12px;")
        mb_lay.addWidget(self._mb_enabled)

        self._mb_angle  = 0
        self._mb_strength = 15
        _slider_row(mb_lay, "Angle",    0, 360, 0,  self._set_mb_angle,    "°")
        _slider_row(mb_lay, "Strength", 1, 50,  15, self._set_mb_strength, "px")

        apply_mb = QPushButton("Apply to Clip")
        apply_mb.setFixedHeight(30)
        apply_mb.setStyleSheet("QPushButton{background:#333;color:#ccc;border-radius:4px;}"
                                "QPushButton:hover{background:#fe2c55;color:white;}")
        apply_mb.clicked.connect(self._emit_motion_blur)
        mb_lay.addWidget(apply_mb)
        lay.addWidget(mb_grp)

        # Zoom Blur
        zb_grp = QGroupBox("Zoom Blur")
        zb_grp.setStyleSheet(mb_grp.styleSheet())
        zb_lay = QVBoxLayout(zb_grp)

        self._zb_strength = 50
        self._zb_cx = 50
        self._zb_cy = 50
        _slider_row(zb_lay, "Strength",   0, 100, 50, self._set_zb_strength, "%")
        _slider_row(zb_lay, "Center X",   0, 100, 50, self._set_zb_cx,       "%")
        _slider_row(zb_lay, "Center Y",   0, 100, 50, self._set_zb_cy,       "%")

        apply_zb = QPushButton("Apply to Clip")
        apply_zb.setFixedHeight(30)
        apply_zb.setStyleSheet(apply_mb.styleSheet())
        apply_zb.clicked.connect(self._emit_zoom_blur)
        zb_lay.addWidget(apply_zb)
        lay.addWidget(zb_grp)

        # Radial Blur
        rb_grp = QGroupBox("Radial / Spin Blur")
        rb_grp.setStyleSheet(mb_grp.styleSheet())
        rb_lay = QVBoxLayout(rb_grp)

        self._rb_strength = 50
        _slider_row(rb_lay, "Strength", 0, 100, 50, self._set_rb_strength, "%")

        apply_rb = QPushButton("Apply to Clip")
        apply_rb.setFixedHeight(30)
        apply_rb.setStyleSheet(apply_mb.styleSheet())
        apply_rb.clicked.connect(self._emit_radial_blur)
        rb_lay.addWidget(apply_rb)
        lay.addWidget(rb_grp)

        # Camera Shake
        from src.core.fx_motion import SHAKE_PRESETS
        cs_grp = QGroupBox("Camera Shake")
        cs_grp.setStyleSheet(mb_grp.styleSheet())
        cs_lay = QVBoxLayout(cs_grp)
        self._cs = {"amount": 40, "speed": 40}
        self._cs_pulse = False
        pre = QComboBox()
        pre.addItems(["Custom"] + list(SHAKE_PRESETS))
        pre.activated.connect(lambda _: self._cs_preset(pre.currentText(), sliders))
        cs_lay.addWidget(pre)
        sliders = {
            "amount": _slider_row(cs_lay, "Amount", 0, 100, 40, lambda v: self._cs.__setitem__("amount", v), "%"),
            "speed": _slider_row(cs_lay, "Speed", 0, 100, 40, lambda v: self._cs.__setitem__("speed", v), "%"),
        }
        apply_cs = QPushButton("Apply to Clip")
        apply_cs.setFixedHeight(30)
        apply_cs.setStyleSheet(apply_mb.styleSheet())
        apply_cs.clicked.connect(self._emit_shake)
        cs_lay.addWidget(apply_cs)
        lay.addWidget(cs_grp)

        # 3D Zoom
        z3_grp = QGroupBox("3D Zoom")
        z3_grp.setStyleSheet(mb_grp.styleSheet())
        z3_lay = QVBoxLayout(z3_grp)
        self._z3 = {"zoom": 120, "rx": 6, "ry": 6}
        _slider_row(z3_lay, "Zoom", 100, 200, 120, lambda v: self._z3.__setitem__("zoom", v), "%")
        _slider_row(z3_lay, "Tilt X", -15, 15, 6, lambda v: self._z3.__setitem__("rx", v), "°")
        _slider_row(z3_lay, "Tilt Y", -15, 15, 6, lambda v: self._z3.__setitem__("ry", v), "°")
        apply_z3 = QPushButton("Apply to Clip (animates over clip)")
        apply_z3.setFixedHeight(30)
        apply_z3.setStyleSheet(apply_mb.styleSheet())
        apply_z3.clicked.connect(self._emit_zoom_3d)
        z3_lay.addWidget(apply_z3)
        lay.addWidget(z3_grp)

        lay.addStretch()
        scroll.setWidget(container)
        out = QVBoxLayout(w)
        out.setContentsMargins(0, 0, 0, 0)
        out.addWidget(scroll)
        return w

    # ── Tab 2: Cinematic ──────────────────────────────────────────────────────

    def _build_cinematic_tab(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        # Ken Burns
        kb_grp = QGroupBox("Ken Burns (Slow Zoom + Pan)")
        kb_grp.setStyleSheet("QGroupBox{color:#aaa;border:1px solid #333;border-radius:6px;"
                              "margin-top:8px;padding-top:6px;}")
        kb_lay = QVBoxLayout(kb_grp)

        self._kb_enabled = QCheckBox("Enable Ken Burns")
        self._kb_enabled.setStyleSheet("color:white;font-size:12px;")
        kb_lay.addWidget(self._kb_enabled)

        # Direction presets
        preset_lbl = QLabel("Preset Direction")
        preset_lbl.setStyleSheet("color:#aaa;font-size:11px;background:transparent;")
        kb_lay.addWidget(preset_lbl)

        self._kb_preset = QComboBox()
        self._kb_preset.addItems([
            "Zoom In (center)",
            "Zoom Out (center)",
            "Pan Left",
            "Pan Right",
            "Diagonal ↗",
            "Diagonal ↙",
            "Custom",
        ])
        self._kb_preset.setStyleSheet("background:#333;color:white;border:1px solid #555;"
                                       "border-radius:4px;padding:3px;")
        self._kb_preset.currentIndexChanged.connect(self._on_kb_preset)
        kb_lay.addWidget(self._kb_preset)

        self._kb_start_scale = 100
        self._kb_end_scale   = 130
        self._kb_start_x     = 50
        self._kb_start_y     = 50
        self._kb_end_x       = 50
        self._kb_end_y       = 50

        _slider_row(kb_lay, "Start Scale", 80,  200, 100, self._set_kb_ss,  "%")
        _slider_row(kb_lay, "End Scale",   80,  200, 130, self._set_kb_es,  "%")
        _slider_row(kb_lay, "Start X",      0,  100, 50,  self._set_kb_sx,  "%")
        _slider_row(kb_lay, "Start Y",      0,  100, 50,  self._set_kb_sy,  "%")
        _slider_row(kb_lay, "End X",        0,  100, 50,  self._set_kb_ex,  "%")
        _slider_row(kb_lay, "End Y",        0,  100, 50,  self._set_kb_ey,  "%")

        apply_kb = QPushButton("Apply Ken Burns to Clip")
        apply_kb.setFixedHeight(30)
        apply_kb.setStyleSheet("QPushButton{background:#333;color:#ccc;border-radius:4px;}"
                                "QPushButton:hover{background:#fe2c55;color:white;}")
        apply_kb.clicked.connect(self._emit_ken_burns)
        kb_lay.addWidget(apply_kb)
        lay.addWidget(kb_grp)

        # Tilt-Shift
        ts_grp = QGroupBox("Tilt-Shift (Miniature)")
        ts_grp.setStyleSheet(kb_grp.styleSheet())
        ts_lay = QVBoxLayout(ts_grp)

        self._ts_focus   = 50
        self._ts_blur    = 15
        self._ts_fade    = 30
        _slider_row(ts_lay, "Focus Band Y",  0, 100, 50, self._set_ts_focus, "%")
        _slider_row(ts_lay, "Blur Amount",   1,  50, 15, self._set_ts_blur,  "px")
        _slider_row(ts_lay, "Fade Range",    5,  80, 30, self._set_ts_fade,  "%")

        apply_ts = QPushButton("Apply Tilt-Shift to Clip")
        apply_ts.setFixedHeight(30)
        apply_ts.setStyleSheet(apply_kb.styleSheet())
        apply_ts.clicked.connect(self._emit_tilt_shift)
        ts_lay.addWidget(apply_ts)
        lay.addWidget(ts_grp)

        lay.addStretch()
        scroll.setWidget(container)
        out = QVBoxLayout(w)
        out.setContentsMargins(0, 0, 0, 0)
        out.addWidget(scroll)
        return w

    # ── Tab 3: Glitch ─────────────────────────────────────────────────────────

    def _build_glitch_tab(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;}")
        container = QWidget()
        lay = QVBoxLayout(container)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        grp_style = ("QGroupBox{color:#aaa;border:1px solid #333;border-radius:6px;"
                     "margin-top:8px;padding-top:6px;}")
        btn_style = ("QPushButton{background:#333;color:#ccc;border-radius:4px;}"
                     "QPushButton:hover{background:#fe2c55;color:white;}")

        # Glitch RGB
        gr_grp = QGroupBox("RGB Glitch")
        gr_grp.setStyleSheet(grp_style)
        gr_lay = QVBoxLayout(gr_grp)

        self._gr_intensity = 50
        _slider_row(gr_lay, "Intensity", 0, 100, 50, self._set_gr_intensity, "%")

        apply_gr = QPushButton("Apply RGB Glitch")
        apply_gr.setFixedHeight(30)
        apply_gr.setStyleSheet(btn_style)
        apply_gr.clicked.connect(self._emit_glitch_rgb)
        gr_lay.addWidget(apply_gr)
        lay.addWidget(gr_grp)

        # VHS Wobble
        vhs_grp = QGroupBox("VHS Wobble")
        vhs_grp.setStyleSheet(grp_style)
        vhs_lay = QVBoxLayout(vhs_grp)

        self._vhs_intensity = 50
        _slider_row(vhs_lay, "Intensity", 0, 100, 50, self._set_vhs_intensity, "%")

        apply_vhs = QPushButton("Apply VHS Wobble")
        apply_vhs.setFixedHeight(30)
        apply_vhs.setStyleSheet(btn_style)
        apply_vhs.clicked.connect(self._emit_vhs)
        vhs_lay.addWidget(apply_vhs)
        lay.addWidget(vhs_grp)

        # Chromatic Aberration
        ca_grp = QGroupBox("Chromatic Aberration")
        ca_grp.setStyleSheet(grp_style)
        ca_lay = QVBoxLayout(ca_grp)

        self._ca_amount = 50
        _slider_row(ca_lay, "Amount", 0, 100, 50, self._set_ca_amount, "%")

        apply_ca = QPushButton("Apply Chromatic Aberration")
        apply_ca.setFixedHeight(30)
        apply_ca.setStyleSheet(btn_style)
        apply_ca.clicked.connect(self._emit_chromatic)
        ca_lay.addWidget(apply_ca)
        lay.addWidget(ca_grp)

        lay.addStretch()
        scroll.setWidget(container)
        out = QVBoxLayout(w)
        out.setContentsMargins(0, 0, 0, 0)
        out.addWidget(scroll)
        return w

    # ── Setters ───────────────────────────────────────────────────────────────

    def _set_mb_angle(self, v):    self._mb_angle = v
    def _set_mb_strength(self, v): self._mb_strength = v
    def _set_zb_strength(self, v): self._zb_strength = v
    def _set_zb_cx(self, v):       self._zb_cx = v
    def _set_zb_cy(self, v):       self._zb_cy = v
    def _set_rb_strength(self, v): self._rb_strength = v
    def _set_kb_ss(self, v):       self._kb_start_scale = v
    def _set_kb_es(self, v):       self._kb_end_scale = v
    def _set_kb_sx(self, v):       self._kb_start_x = v
    def _set_kb_sy(self, v):       self._kb_start_y = v
    def _set_kb_ex(self, v):       self._kb_end_x = v
    def _set_kb_ey(self, v):       self._kb_end_y = v
    def _set_ts_focus(self, v):    self._ts_focus = v
    def _set_ts_blur(self, v):     self._ts_blur = v
    def _set_ts_fade(self, v):     self._ts_fade = v
    def _set_gr_intensity(self, v): self._gr_intensity = v
    def _set_vhs_intensity(self, v): self._vhs_intensity = v
    def _set_ca_amount(self, v):   self._ca_amount = v

    def _on_kb_preset(self, idx: int):
        presets = [
            # start_scale, end_scale, sx, sy, ex, ey
            (100, 130, 50, 50, 50, 50),   # Zoom In center
            (130, 100, 50, 50, 50, 50),   # Zoom Out center
            (110, 110, 70, 50, 30, 50),   # Pan Left
            (110, 110, 30, 50, 70, 50),   # Pan Right
            (100, 130, 30, 70, 70, 30),   # Diagonal ↗
            (100, 130, 70, 30, 30, 70),   # Diagonal ↙
        ]
        if idx < len(presets):
            ss, es, sx, sy, ex, ey = presets[idx]
            self._kb_start_scale = ss
            self._kb_end_scale   = es
            self._kb_start_x     = sx
            self._kb_start_y     = sy
            self._kb_end_x       = ex
            self._kb_end_y       = ey

    # ── Emitters ──────────────────────────────────────────────────────────────

    def _emit_motion_blur(self):
        self.effect_params_changed.emit("motion_blur", {
            "enabled":  self._mb_enabled.isChecked(),
            "angle":    float(self._mb_angle),
            "strength": int(self._mb_strength),
        })

    def _emit_zoom_blur(self):
        self.effect_params_changed.emit("zoom_blur", {
            "strength": self._zb_strength / 100.0,
            "center_x": self._zb_cx / 100.0,
            "center_y": self._zb_cy / 100.0,
        })

    def _cs_preset(self, name, sliders):
        from src.core.fx_motion import SHAKE_PRESETS
        p = SHAKE_PRESETS.get(name)
        if not p:
            return
        self._cs_pulse = bool(p.get('pulse'))
        sliders["amount"].setValue(int(p['amount'] * 100))
        sliders["speed"].setValue(int(p['speed'] * 100))

    def _emit_shake(self):
        self.effect_params_changed.emit("camera_shake", {
            "amount": self._cs["amount"] / 100.0, "speed": self._cs["speed"] / 100.0,
            "pulse": self._cs_pulse, "seed": 7,
        })

    def _emit_zoom_3d(self):
        self.effect_params_changed.emit("zoom_3d", {
            "zoom": self._z3["zoom"] / 100.0, "rotation_x": float(self._z3["rx"]),
            "rotation_y": float(self._z3["ry"]), "animate": True,
        })

    def _emit_radial_blur(self):
        self.effect_params_changed.emit("radial_blur", {
            "strength": self._rb_strength / 100.0,
        })

    def _emit_ken_burns(self):
        self.effect_params_changed.emit("ken_burns", {
            "enabled":     self._kb_enabled.isChecked(),
            "start_scale": self._kb_start_scale / 100.0,
            "end_scale":   self._kb_end_scale / 100.0,
            "start_x":     self._kb_start_x / 100.0,
            "start_y":     self._kb_start_y / 100.0,
            "end_x":       self._kb_end_x / 100.0,
            "end_y":       self._kb_end_y / 100.0,
        })

    def _emit_tilt_shift(self):
        self.effect_params_changed.emit("tilt_shift", {
            "focus_y":     self._ts_focus / 100.0,
            "blur_amount": int(self._ts_blur),
            "fade_range":  self._ts_fade / 100.0,
        })

    def _emit_glitch_rgb(self):
        self.effect_params_changed.emit("glitch_rgb", {
            "intensity": self._gr_intensity / 100.0,
        })

    def _emit_vhs(self):
        self.effect_params_changed.emit("vhs_wobble", {
            "intensity": self._vhs_intensity / 100.0,
        })

    def _emit_chromatic(self):
        self.effect_params_changed.emit("chromatic_aberration", {
            "amount": self._ca_amount / 100.0,
        })
