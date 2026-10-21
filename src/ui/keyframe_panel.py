"""
Keyframe Animation Panel — add/remove keyframes, pick easing, per-property sliders.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QFrame, QComboBox, QScrollArea, QListWidget,
    QListWidgetItem, QSpinBox, QDoubleSpinBox,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from src.core.keyframe_engine import KeyframeAnimator, ANIMATABLE_PROPS


def _sec(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "color:#fe2c55;font-size:11px;font-weight:bold;"
        "background:transparent;margin-top:6px;"
    )
    return lbl


def _div() -> QFrame:
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet("color:#2a2a2a;")
    return f


class KeyframePanel(QWidget):
    keyframe_changed = pyqtSignal(str, float, dict)   # clip_id, time, props
    keyframe_removed = pyqtSignal(str, float)          # clip_id, time

    def __init__(self, animator: KeyframeAnimator, parent=None):
        super().__init__(parent)
        self._animator = animator
        self._clip_id  = ""
        self._current_time = 0.0
        self._prop_sliders: dict = {}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        hdr = QWidget()
        hdr.setFixedHeight(40)
        hdr.setStyleSheet("background:#111111;border-bottom:1px solid #2a2a2a;")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(12, 0, 12, 0)
        title = QLabel("🎞 Keyframe Animation")
        title.setStyleSheet("color:#fff;font-size:13px;font-weight:bold;background:transparent;")
        hdr_lay.addWidget(title)
        root.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea{border:none;}")

        body = QWidget()
        lay = QVBoxLayout(body)
        lay.setContentsMargins(12, 12, 12, 12)
        lay.setSpacing(4)

        # ── Clip info ─────────────────────────────────────────────────
        clip_row = QHBoxLayout()
        clip_lbl = QLabel("Clip:")
        clip_lbl.setFixedWidth(40)
        clip_lbl.setStyleSheet("color:#aaa;font-size:12px;background:transparent;")
        clip_row.addWidget(clip_lbl)
        self._clip_lbl = QLabel("(none selected)")
        self._clip_lbl.setStyleSheet("color:#fff;font-size:12px;background:transparent;")
        clip_row.addWidget(self._clip_lbl, 1)
        lay.addLayout(clip_row)

        # ── Current time ──────────────────────────────────────────────
        time_row = QHBoxLayout()
        time_lbl = QLabel("Time:")
        time_lbl.setFixedWidth(40)
        time_lbl.setStyleSheet("color:#aaa;font-size:12px;background:transparent;")
        time_row.addWidget(time_lbl)
        self._time_spin = QDoubleSpinBox()
        self._time_spin.setRange(0, 9999)
        self._time_spin.setDecimals(2)
        self._time_spin.setSingleStep(0.1)
        self._time_spin.setSuffix(" s")
        self._time_spin.setStyleSheet(
            "background:#2a2a2a;color:white;border:1px solid #444;"
            "border-radius:4px;padding:2px;min-width:80px;"
        )
        self._time_spin.valueChanged.connect(self._on_time_changed)
        time_row.addWidget(self._time_spin)
        time_row.addStretch()
        lay.addLayout(time_row)
        lay.addWidget(_div())

        # ── Easing ────────────────────────────────────────────────────
        lay.addWidget(_sec("EASING"))
        ease_row = QHBoxLayout()
        ease_lbl = QLabel("Curve:")
        ease_lbl.setFixedWidth(50)
        ease_lbl.setStyleSheet("color:#aaa;font-size:11px;background:transparent;")
        ease_row.addWidget(ease_lbl)
        self._ease_combo = QComboBox()
        self._ease_combo.addItems([
            "ease_in_out", "linear", "ease_in", "ease_out", "bounce", "elastic",
            "bezier:0.25,0.1,0.25,1", "bezier:0.34,1.56,0.64,1", "bezier:0.9,0,0.1,1"
        ])
        for i, tip in ((6, "Ease"), (7, "Back-out (overshoot)"), (8, "Snap")):
            self._ease_combo.setItemData(i, tip, Qt.ItemDataRole.ToolTipRole)
        self._ease_combo.setStyleSheet(
            "QComboBox{background:#2a2a2a;color:#ccc;border:1px solid #3a3a3a;"
            "border-radius:4px;padding:3px 8px;}"
            "QComboBox QAbstractItemView{background:#2a2a2a;color:#ccc;}"
        )
        ease_row.addWidget(self._ease_combo)
        ease_row.addStretch()
        lay.addLayout(ease_row)
        lay.addWidget(_div())

        # ── Animatable properties ─────────────────────────────────────
        lay.addWidget(_sec("PROPERTIES"))

        for prop, (mn, mx, default) in ANIMATABLE_PROPS.items():
            row = QHBoxLayout()
            lbl = QLabel(prop.replace("_", " ").title())
            lbl.setFixedWidth(82)
            lbl.setStyleSheet("color:#aaa;font-size:11px;background:transparent;")
            row.addWidget(lbl)

            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(int(mn * 100), int(mx * 100))
            slider.setValue(int(default * 100))
            row.addWidget(slider, 1)

            val_lbl = QLabel(f"{default:.1f}")
            val_lbl.setFixedWidth(38)
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val_lbl.setStyleSheet("color:#ccc;font-size:11px;background:transparent;")
            row.addWidget(val_lbl)

            slider.valueChanged.connect(
                lambda v, vl=val_lbl: vl.setText(f"{v/100:.1f}")
            )
            self._prop_sliders[prop] = (slider, val_lbl)
            lay.addLayout(row)

        lay.addWidget(_div())

        # ── Keyframe list ─────────────────────────────────────────────
        lay.addWidget(_sec("KEYFRAMES ON THIS CLIP"))
        self._kf_list = QListWidget()
        self._kf_list.setMaximumHeight(120)
        self._kf_list.setStyleSheet(
            "QListWidget{background:#2a2a2a;color:#ccc;border:1px solid #333;"
            "border-radius:4px;font-size:11px;}"
            "QListWidget::item:selected{background:#fe2c5540;}"
        )
        self._kf_list.itemClicked.connect(self._on_kf_selected)
        lay.addWidget(self._kf_list)

        rem_btn = QPushButton("🗑  Remove Selected Keyframe")
        rem_btn.setFixedHeight(28)
        rem_btn.setStyleSheet(
            "QPushButton{background:#2a2a2a;color:#ccc;border-radius:4px;"
            "border:1px solid #3a3a3a;font-size:11px;}"
            "QPushButton:hover{border-color:#fe2c55;color:white;}"
        )
        rem_btn.clicked.connect(self._remove_kf)
        lay.addWidget(rem_btn)

        lay.addStretch()
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        # Footer
        footer = QWidget()
        footer.setStyleSheet("background:#111111;border-top:1px solid #2a2a2a;")
        foot_lay = QHBoxLayout(footer)
        foot_lay.setContentsMargins(12, 8, 12, 8)
        foot_lay.setSpacing(8)

        add_btn = QPushButton("+ Add Keyframe")
        add_btn.setFixedHeight(34)
        add_btn.setStyleSheet(
            "QPushButton{background:#2a2a2a;color:#ccc;border-radius:6px;"
            "border:1px solid #444;font-size:12px;}"
            "QPushButton:hover{background:#333;border-color:#fe2c55;}"
        )
        add_btn.clicked.connect(self._add_kf)
        foot_lay.addWidget(add_btn)

        clear_btn = QPushButton("Clear All")
        clear_btn.setFixedHeight(34)
        clear_btn.setStyleSheet(
            "QPushButton{background:#2a2a2a;color:#888;border-radius:6px;"
            "border:1px solid #333;font-size:12px;}"
            "QPushButton:hover{color:#fe2c55;}"
        )
        clear_btn.clicked.connect(self._clear_all)
        foot_lay.addWidget(clear_btn)

        root.addWidget(footer)

    # ── Slots ──────────────────────────────────────────────────────────────

    def set_clip(self, clip_id: str):
        self._clip_id = clip_id
        self._clip_lbl.setText(clip_id or "(none selected)")
        self._refresh_kf_list()

    def set_time(self, t: float):
        self._current_time = t
        self._time_spin.blockSignals(True)
        self._time_spin.setValue(t)
        self._time_spin.blockSignals(False)
        self._load_props_at(t)

    def _on_time_changed(self, t: float):
        self._current_time = t
        self._load_props_at(t)

    def _load_props_at(self, t: float):
        if not self._clip_id:
            return
        props = self._animator.get_props_at(self._clip_id, t)
        for prop, (slider, val_lbl) in self._prop_sliders.items():
            if prop in props:
                slider.blockSignals(True)
                slider.setValue(int(props[prop] * 100))
                val_lbl.setText(f"{props[prop]:.1f}")
                slider.blockSignals(False)

    def _get_current_props(self) -> dict:
        result = {}
        for prop, (slider, _) in self._prop_sliders.items():
            result[prop] = slider.value() / 100.0
        return result

    def _add_kf(self):
        if not self._clip_id:
            return
        props  = self._get_current_props()
        easing = self._ease_combo.currentText()
        t      = self._current_time
        self._animator.set_keyframe(self._clip_id, t, props, easing)
        self._refresh_kf_list()
        self.keyframe_changed.emit(self._clip_id, t, props)

    def _remove_kf(self):
        item = self._kf_list.currentItem()
        if not item or not self._clip_id:
            return
        t = float(item.data(Qt.ItemDataRole.UserRole))
        self._animator.remove_keyframe(self._clip_id, t)
        self._refresh_kf_list()
        self.keyframe_removed.emit(self._clip_id, t)

    def _clear_all(self):
        if self._clip_id:
            self._animator.clear_clip(self._clip_id)
            self._refresh_kf_list()
            self.keyframe_removed.emit(self._clip_id, -1.0)

    def _refresh_kf_list(self):
        self._kf_list.clear()
        if not self._clip_id:
            return
        track = self._animator.get_track(self._clip_id)
        for kf in track.keyframes:
            item = QListWidgetItem(
                f"  {kf.time:.2f}s  —  {kf.easing}  —  {len(kf.props)} props"
            )
            item.setData(Qt.ItemDataRole.UserRole, kf.time)
            self._kf_list.addItem(item)

    def _on_kf_selected(self, item: QListWidgetItem):
        t = float(item.data(Qt.ItemDataRole.UserRole))
        self._time_spin.setValue(t)
        self._load_props_at(t)
