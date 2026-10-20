"""
Properties Panel - Right panel for clip properties: color, transform, speed, text
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSlider, QScrollArea, QGroupBox, QGridLayout, QTabWidget,
    QLineEdit, QSpinBox, QDoubleSpinBox, QCheckBox, QComboBox,
    QFrame, QSizePolicy, QColorDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont

from src.core.project import Clip, ClipType


class SliderRow(QWidget):
    value_changed = pyqtSignal(float)

    def __init__(self, label: str, min_val: float, max_val: float,
                 default: float = 0.0, step: float = 1.0, parent=None):
        super().__init__(parent)
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self._updating = False

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(6)

        # Label
        lbl = QLabel(label)
        lbl.setFixedWidth(80)
        lbl.setStyleSheet("color: #aaaaaa; font-size: 11px; background: transparent;")
        layout.addWidget(lbl)

        # Slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        int_range = int((max_val - min_val) / step * 100)
        self.slider.setRange(0, int_range)
        self.slider.valueChanged.connect(self._on_slider)
        layout.addWidget(self.slider, 1)

        # Value label / spinbox
        self.val_lbl = QLabel("0.0")
        self.val_lbl.setFixedWidth(38)
        self.val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.val_lbl.setStyleSheet("color: #cccccc; font-size: 11px; background: transparent;")
        layout.addWidget(self.val_lbl)

        # Reset button
        reset_btn = QPushButton("↺")
        reset_btn.setFixedSize(18, 18)
        reset_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #666; font-size: 11px; border: none;
            }
            QPushButton:hover { color: #fe2c55; }
        """)
        reset_btn.clicked.connect(lambda: self.set_value(default))
        layout.addWidget(reset_btn)

        self.set_value(default)

    def _on_slider(self, v: int):
        if not self._updating:
            real_val = self.min_val + v / 100.0 * self.step
            display = f"{real_val:.2f}".rstrip('0').rstrip('.')
            self.val_lbl.setText(display)
            self.value_changed.emit(real_val)

    def set_value(self, val: float):
        self._updating = True
        slider_val = int((val - self.min_val) / self.step * 100)
        self.slider.setValue(max(0, min(slider_val, self.slider.maximum())))
        display = f"{val:.2f}".rstrip('0').rstrip('.')
        self.val_lbl.setText(display if display else "0")
        self._updating = False

    def get_value(self) -> float:
        return self.min_val + self.slider.value() / 100.0 * self.step


class ColorButton(QPushButton):
    color_changed = pyqtSignal(str)

    def __init__(self, color: str = "#ffffff", parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 24)
        self._color = color
        self._update_style()
        self.clicked.connect(self._pick_color)

    def _update_style(self):
        self.setStyleSheet(f"""
            QPushButton {{
                background: {self._color};
                border: 1px solid #555555;
                border-radius: 4px;
            }}
            QPushButton:hover {{ border-color: #fe2c55; }}
        """)

    def _pick_color(self):
        col = QColorDialog.getColor(QColor(self._color), self, "Pick Color")
        if col.isValid():
            self._color = col.name()
            self._update_style()
            self.color_changed.emit(self._color)

    def set_color(self, color: str):
        self._color = color
        self._update_style()

    def get_color(self) -> str:
        return self._color


class PropertiesPanel(QWidget):
    clip_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.clip = None
        self._updating = False
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(40)
        header.setStyleSheet("background: #111111; border-bottom: 1px solid #2a2a2a;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)
        self.header_label = QLabel("Properties")
        self.header_label.setStyleSheet("color: #ffffff; font-size: 13px; font-weight: bold; background: transparent;")
        header_layout.addWidget(self.header_label)
        layout.addWidget(header)

        # Empty state
        self.empty_state = QLabel("Select a clip\nto edit properties")
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state.setStyleSheet("color: #555555; font-size: 12px;")
        layout.addWidget(self.empty_state)

        # Tabs (hidden until clip selected)
        self.tabs = QTabWidget()
        self.tabs.setVisible(False)
        self.tabs.setStyleSheet("""
            QTabBar::tab { padding: 6px 8px; font-size: 11px; }
        """)

        # Color tab
        self.color_tab = self._build_color_tab()
        self.tabs.addTab(self.color_tab, "Color")

        # Transform tab
        self.transform_tab = self._build_transform_tab()
        self.tabs.addTab(self.transform_tab, "Transform")

        # Speed tab
        self.speed_tab = self._build_speed_tab()
        self.tabs.addTab(self.speed_tab, "Speed")

        # Text tab (shown when text clip)
        self.text_tab = self._build_text_props_tab()
        self.tabs.addTab(self.text_tab, "Text")

        # Audio tab
        self.audio_tab = self._build_audio_tab()
        self.tabs.addTab(self.audio_tab, "Audio")

        # Beauty tab
        self.beauty_tab = self._build_beauty_tab()
        self.tabs.addTab(self.beauty_tab, "💄 Beauty")

        # Grade tab
        self.grade_tab = self._build_grade_tab()
        self.tabs.addTab(self.grade_tab, "🎬 Grade")

        # Chroma / Mask tab
        self.chroma_tab = self._build_chroma_tab()
        self.tabs.addTab(self.chroma_tab, "🟩 Chroma")

        layout.addWidget(self.tabs, 1)

    def _build_color_tab(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(2)

        self.sliders_color = {}
        color_props = [
            ("Brightness", "brightness", -1.0, 1.0, 0.0),
            ("Contrast", "contrast", -1.0, 1.0, 0.0),
            ("Saturation", "saturation", -1.0, 1.0, 0.0),
            ("Temperature", "temperature", -1.0, 1.0, 0.0),
            ("Tint", "tint", -1.0, 1.0, 0.0),
            ("Highlight", "highlight", -1.0, 1.0, 0.0),
            ("Shadow", "shadow", -1.0, 1.0, 0.0),
            ("Sharpness", "sharpness", 0.0, 1.0, 0.0),
            ("Vignette", "vignette", 0.0, 2.0, 0.0),
            ("Fade In", "fade_in", 0.0, 3.0, 0.0),
            ("Fade Out", "fade_out", 0.0, 3.0, 0.0),
        ]

        for label, attr, mn, mx, default in color_props:
            sl = SliderRow(label, mn, mx, default, mx - mn)
            sl.value_changed.connect(lambda v, a=attr: self._set_clip_attr(a, v))
            self.sliders_color[attr] = sl
            layout.addWidget(sl)

        layout.addStretch()
        scroll.setWidget(container)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return w

    def _build_transform_tab(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)

        # Position
        pos_label = QLabel("POSITION")
        pos_label.setObjectName("sectionTitle")
        layout.addWidget(pos_label)

        self.pos_x = SliderRow("X", 0.0, 1.0, 0.5, 1.0)
        self.pos_x.value_changed.connect(lambda v: self._set_clip_attr("position_x", v))
        layout.addWidget(self.pos_x)

        self.pos_y = SliderRow("Y", 0.0, 1.0, 0.5, 1.0)
        self.pos_y.value_changed.connect(lambda v: self._set_clip_attr("position_y", v))
        layout.addWidget(self.pos_y)

        # Scale
        scale_label = QLabel("SCALE")
        scale_label.setObjectName("sectionTitle")
        layout.addWidget(scale_label)

        self.scale_x = SliderRow("Scale X", 0.1, 3.0, 1.0, 2.9)
        self.scale_x.value_changed.connect(lambda v: self._set_clip_attr("scale_x", v))
        layout.addWidget(self.scale_x)

        self.scale_y = SliderRow("Scale Y", 0.1, 3.0, 1.0, 2.9)
        self.scale_y.value_changed.connect(lambda v: self._set_clip_attr("scale_y", v))
        layout.addWidget(self.scale_y)

        # Rotation
        rot_label = QLabel("ROTATION")
        rot_label.setObjectName("sectionTitle")
        layout.addWidget(rot_label)

        self.rotation = SliderRow("Rotation", -180.0, 180.0, 0.0, 360.0)
        self.rotation.value_changed.connect(lambda v: self._set_clip_attr("rotation", v))
        layout.addWidget(self.rotation)

        # Opacity
        opa_label = QLabel("OPACITY")
        opa_label.setObjectName("sectionTitle")
        layout.addWidget(opa_label)

        self.opacity = SliderRow("Opacity", 0.0, 1.0, 1.0, 1.0)
        self.opacity.value_changed.connect(lambda v: self._set_clip_attr("opacity", v))
        layout.addWidget(self.opacity)

        # Flip
        flip_row = QHBoxLayout()
        flip_label = QLabel("FLIP")
        flip_label.setObjectName("sectionTitle")
        layout.addWidget(flip_label)

        self.flip_h_btn = QPushButton("↔ Flip H")
        self.flip_h_btn.setFixedHeight(30)
        self.flip_h_btn.setStyleSheet("""
            QPushButton { background: #333; color: #ccc; border-radius: 4px; font-size: 11px; }
            QPushButton:hover { background: #444; }
            QPushButton:checked { background: #fe2c55; color: white; }
        """)
        self.flip_h_btn.setCheckable(True)
        self.flip_h_btn.toggled.connect(lambda v: self._set_clip_attr("flip_h", v))
        flip_row.addWidget(self.flip_h_btn)

        self.flip_v_btn = QPushButton("↕ Flip V")
        self.flip_v_btn.setFixedHeight(30)
        self.flip_v_btn.setStyleSheet(self.flip_h_btn.styleSheet())
        self.flip_v_btn.setCheckable(True)
        self.flip_v_btn.toggled.connect(lambda v: self._set_clip_attr("flip_v", v))
        flip_row.addWidget(self.flip_v_btn)

        layout.addLayout(flip_row)

        # Crop
        crop_label = QLabel("CROP")
        crop_label.setObjectName("sectionTitle")
        layout.addWidget(crop_label)

        self.crop_sliders = {}
        for side in ['crop_left', 'crop_right', 'crop_top', 'crop_bottom']:
            label = side.replace('_', ' ').title()
            sl = SliderRow(label, 0.0, 0.5, 0.0, 0.5)
            sl.value_changed.connect(lambda v, a=side: self._set_clip_attr(a, v))
            self.crop_sliders[side] = sl
            layout.addWidget(sl)

        layout.addStretch()
        scroll.setWidget(container)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return w

    def _build_speed_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Speed presets
        presets_label = QLabel("SPEED PRESETS")
        presets_label.setObjectName("sectionTitle")
        layout.addWidget(presets_label)

        presets_row = QHBoxLayout()
        speeds = [("0.25x", 0.25), ("0.5x", 0.5), ("0.75x", 0.75),
                  ("1x", 1.0), ("1.5x", 1.5), ("2x", 2.0), ("4x", 4.0)]
        for label, val in speeds:
            btn = QPushButton(label)
            btn.setFixedHeight(28)
            btn.setStyleSheet("""
                QPushButton { background: #333; color: #ccc; border-radius: 4px; font-size: 10px; }
                QPushButton:hover { background: #fe2c55; color: white; }
            """)
            btn.clicked.connect(lambda checked, v=val: self._set_speed(v))
            presets_row.addWidget(btn)

        layout.addLayout(presets_row)

        # Custom speed
        speed_label = QLabel("CUSTOM SPEED")
        speed_label.setObjectName("sectionTitle")
        layout.addWidget(speed_label)

        self.speed_slider = SliderRow("Speed", 0.1, 10.0, 1.0, 9.9)
        self.speed_slider.value_changed.connect(lambda v: self._set_clip_attr("speed", v))
        layout.addWidget(self.speed_slider)

        # Reverse
        self.reverse_check = QCheckBox("Reverse")
        self.reverse_check.setStyleSheet("color: white; font-size: 12px;")
        self.reverse_check.toggled.connect(lambda v: self._set_clip_attr("reverse", v))
        layout.addWidget(self.reverse_check)

        layout.addStretch()
        return w

    def _build_text_props_tab(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Text input
        text_label = QLabel("TEXT CONTENT")
        text_label.setObjectName("sectionTitle")
        layout.addWidget(text_label)

        self.text_input = QLineEdit()
        self.text_input.setPlaceholderText("Enter text...")
        self.text_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.text_input)

        # Font
        font_label = QLabel("FONT")
        font_label.setObjectName("sectionTitle")
        layout.addWidget(font_label)

        self.font_combo = QComboBox()
        fonts = ["Arial", "Helvetica", "Times New Roman", "Courier New",
                 "Georgia", "Verdana", "Impact", "Comic Sans MS",
                 "Trebuchet MS", "Palatino", "Garamond", "Bookman"]
        self.font_combo.addItems(fonts)
        self.font_combo.currentTextChanged.connect(
            lambda t: self._set_text_style("font_family", t))
        layout.addWidget(self.font_combo)

        # Size
        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Size"))
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 200)
        self.font_size.setValue(48)
        self.font_size.valueChanged.connect(lambda v: self._set_text_style("font_size", v))
        size_row.addWidget(self.font_size)
        size_row.addStretch()
        layout.addLayout(size_row)

        # Style
        style_row = QHBoxLayout()
        self.bold_btn = QPushButton("B")
        self.bold_btn.setFixedSize(32, 28)
        self.bold_btn.setCheckable(True)
        self.bold_btn.setStyleSheet("""
            QPushButton { font-weight: bold; background: #333; color: white; border-radius: 4px; }
            QPushButton:checked { background: #fe2c55; }
        """)
        self.bold_btn.toggled.connect(lambda v: self._set_text_style("bold", v))
        style_row.addWidget(self.bold_btn)

        self.italic_btn = QPushButton("I")
        self.italic_btn.setFixedSize(32, 28)
        self.italic_btn.setCheckable(True)
        self.italic_btn.setStyleSheet("""
            QPushButton { font-style: italic; background: #333; color: white; border-radius: 4px; }
            QPushButton:checked { background: #fe2c55; }
        """)
        self.italic_btn.toggled.connect(lambda v: self._set_text_style("italic", v))
        style_row.addWidget(self.italic_btn)

        style_row.addStretch()
        layout.addLayout(style_row)

        # Colors
        color_row = QHBoxLayout()
        color_row.addWidget(QLabel("Text Color"))
        self.text_color_btn = ColorButton("#ffffff")
        self.text_color_btn.color_changed.connect(lambda c: self._set_text_style("color", c))
        color_row.addWidget(self.text_color_btn)
        color_row.addStretch()
        layout.addLayout(color_row)

        stroke_row = QHBoxLayout()
        stroke_row.addWidget(QLabel("Stroke"))
        self.stroke_color_btn = ColorButton("#000000")
        self.stroke_color_btn.color_changed.connect(lambda c: self._set_text_style("stroke_color", c))
        stroke_row.addWidget(self.stroke_color_btn)
        stroke_row.addWidget(QLabel("Width"))
        self.stroke_width = QSpinBox()
        self.stroke_width.setRange(0, 10)
        self.stroke_width.valueChanged.connect(lambda v: self._set_text_style("stroke_width", v))
        stroke_row.addWidget(self.stroke_width)
        layout.addLayout(stroke_row)

        # Shadow
        self.shadow_check = QCheckBox("Shadow")
        self.shadow_check.toggled.connect(lambda v: self._set_text_style("shadow", v))
        layout.addWidget(self.shadow_check)

        layout.addStretch()
        scroll.setWidget(container)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return w

    def _build_audio_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Volume
        vol_label = QLabel("VOLUME")
        vol_label.setObjectName("sectionTitle")
        layout.addWidget(vol_label)

        self.volume_slider = SliderRow("Volume", 0.0, 2.0, 1.0, 2.0)
        self.volume_slider.value_changed.connect(lambda v: self._set_clip_attr("volume", v))
        layout.addWidget(self.volume_slider)

        # Mute
        self.mute_check = QCheckBox("Mute")
        self.mute_check.setStyleSheet("color: white; font-size: 12px;")
        self.mute_check.toggled.connect(lambda v: self._set_clip_attr("muted", v))
        layout.addWidget(self.mute_check)

        # Fade in/out
        fade_label = QLabel("AUDIO FADE")
        fade_label.setObjectName("sectionTitle")
        layout.addWidget(fade_label)

        self.audio_fade_in = SliderRow("Fade In", 0.0, 3.0, 0.0, 3.0)
        self.audio_fade_in.value_changed.connect(lambda v: self._set_clip_attr("audio_fade_in", v))
        layout.addWidget(self.audio_fade_in)

        self.audio_fade_out = SliderRow("Fade Out", 0.0, 3.0, 0.0, 3.0)
        self.audio_fade_out.value_changed.connect(lambda v: self._set_clip_attr("audio_fade_out", v))
        layout.addWidget(self.audio_fade_out)

        layout.addStretch()
        return w

    # ---- Data binding ----

    def set_clip(self, clip: Clip):
        if clip is None:
            self.clear()
            return

        self.clip = clip
        self._updating = True
        self.empty_state.hide()
        self.tabs.setVisible(True)
        self.header_label.setText(f"Properties — {clip.clip_type.value.title()}")

        # Show/hide text tab
        text_tab_idx = self.tabs.indexOf(self.text_tab)
        if clip.clip_type == ClipType.TEXT:
            self.tabs.setTabVisible(text_tab_idx, True)
        else:
            self.tabs.setTabVisible(text_tab_idx, False)

        # Color
        for attr, sl in self.sliders_color.items():
            sl.set_value(getattr(clip, attr, 0.0))

        # Transform
        self.pos_x.set_value(clip.position_x)
        self.pos_y.set_value(clip.position_y)
        self.scale_x.set_value(clip.scale_x)
        self.scale_y.set_value(clip.scale_y)
        self.rotation.set_value(clip.rotation)
        self.opacity.set_value(clip.opacity)
        self.flip_h_btn.setChecked(clip.flip_h)
        self.flip_v_btn.setChecked(clip.flip_v)
        for side, sl in self.crop_sliders.items():
            sl.set_value(getattr(clip, side, 0.0))

        # Speed
        self.speed_slider.set_value(clip.speed)
        self.reverse_check.setChecked(clip.reverse)

        # Text
        if clip.clip_type == ClipType.TEXT:
            self.text_input.setText(clip.text_content)
            idx = self.font_combo.findText(clip.text_style.font_family)
            if idx >= 0:
                self.font_combo.setCurrentIndex(idx)
            self.font_size.setValue(clip.text_style.font_size)
            self.bold_btn.setChecked(clip.text_style.bold)
            self.italic_btn.setChecked(clip.text_style.italic)
            self.text_color_btn.set_color(clip.text_style.color)
            self.stroke_color_btn.set_color(clip.text_style.stroke_color)
            self.stroke_width.setValue(clip.text_style.stroke_width)
            self.shadow_check.setChecked(clip.text_style.shadow)

        # Audio
        self.volume_slider.set_value(clip.volume)
        self.mute_check.setChecked(clip.muted)
        self.audio_fade_in.set_value(clip.audio_fade_in)
        self.audio_fade_out.set_value(clip.audio_fade_out)

        # Beauty
        for attr, sl in self.sliders_beauty.items():
            sl.set_value(getattr(clip, attr, 0.0))

        # Grade / LUT
        lut_id = getattr(clip, 'lut_id', '')
        for i in range(self.lut_combo.count()):
            if self.lut_combo.itemData(i) == lut_id:
                self.lut_combo.setCurrentIndex(i)
                break
        self.lut_strength.set_value(getattr(clip, 'lut_strength', 1.0))

        # Mask
        mask_type = getattr(clip, 'mask_type', '')
        for i in range(self.mask_combo.count()):
            if self.mask_combo.itemData(i) == mask_type:
                self.mask_combo.setCurrentIndex(i)
                break
        self.mask_feather.set_value(getattr(clip, 'mask_feather', 0.1))
        self.mask_inverted.setChecked(getattr(clip, 'mask_inverted', False))

        # Chroma
        self.chroma_enable.setChecked(getattr(clip, 'chroma_key_enabled', False))
        self.chroma_tolerance_sl.set_value(getattr(clip, 'chroma_key_tolerance', 30.0))
        self.chroma_hue_sl.set_value(getattr(clip, 'chroma_key_hue', 60.0))

        self._updating = False

    def clear(self):
        self.clip = None
        self.tabs.setVisible(False)
        self.empty_state.show()
        self.header_label.setText("Properties")

    def _set_clip_attr(self, attr: str, value):
        if self._updating or not self.clip:
            return
        setattr(self.clip, attr, value)
        self.clip_changed.emit(self.clip.id)

    def _set_speed(self, speed: float):
        if not self.clip:
            return
        self.speed_slider.set_value(speed)
        self.clip.speed = speed
        self.clip_changed.emit(self.clip.id)

    def _on_text_changed(self, text: str):
        if self._updating or not self.clip:
            return
        self.clip.text_content = text
        self.clip_changed.emit(self.clip.id)

    def _build_beauty_tab(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(2)

        self.sliders_beauty = {}
        beauty_props = [
            ("Skin Smooth", "skin_smooth", 0.0, 1.0, 0.0),
            ("Whitening", "whitening", 0.0, 1.0, 0.0),
            ("Noise Reduce", "noise_reduction", 0.0, 1.0, 0.0),
            ("Skin Tone", "skin_tone", -1.0, 1.0, 0.0),
            ("Clarity", "clarity", 0.0, 1.0, 0.0),
            ("Grain", "grain", 0.0, 1.0, 0.0),
            ("Dehaze", "dehaze", 0.0, 1.0, 0.0),
        ]

        for label, attr, mn, mx, default in beauty_props:
            sl = SliderRow(label, mn, mx, default, mx - mn)
            sl.value_changed.connect(lambda v, a=attr: self._set_clip_attr(a, v))
            self.sliders_beauty[attr] = sl
            layout.addWidget(sl)

        reset_btn = QPushButton("Reset All Beauty")
        reset_btn.setFixedHeight(30)
        reset_btn.setStyleSheet("QPushButton { background: #333; color: #ccc; border-radius: 4px; margin-top: 6px; } QPushButton:hover { background: #444; }")
        reset_btn.clicked.connect(self._reset_beauty)
        layout.addWidget(reset_btn)

        layout.addStretch()
        scroll.setWidget(container)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return w

    def _build_grade_tab(self) -> QWidget:
        w = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        lut_label = QLabel("LUT PRESET")
        lut_label.setObjectName("sectionTitle")
        layout.addWidget(lut_label)

        self.lut_combo = QComboBox()
        lut_options = [
            ("None", ""),
            ("Bleach Bypass", "bleach_bypass"),
            ("Day for Night", "day_for_night"),
            ("Teal & Orange", "teal_orange"),
            ("Blockbuster", "blockbuster"),
        ]
        for name, lid in lut_options:
            self.lut_combo.addItem(name, lid)
        self.lut_combo.setStyleSheet("background: #333; color: white; border: 1px solid #555; border-radius: 4px; padding: 4px;")
        self.lut_combo.currentIndexChanged.connect(self._on_lut_changed)
        layout.addWidget(self.lut_combo)

        self.lut_strength = SliderRow("Strength", 0.0, 1.0, 1.0, 1.0)
        self.lut_strength.value_changed.connect(lambda v: self._set_clip_attr("lut_strength", v))
        layout.addWidget(self.lut_strength)

        mask_label = QLabel("SHAPE MASK")
        mask_label.setObjectName("sectionTitle")
        layout.addWidget(mask_label)

        self.mask_combo = QComboBox()
        mask_options = [("None", ""), ("Circle", "circle"), ("Rectangle", "rect"), ("Star", "star"), ("Heart", "heart")]
        for name, mid in mask_options:
            self.mask_combo.addItem(name, mid)
        self.mask_combo.setStyleSheet("background: #333; color: white; border: 1px solid #555; border-radius: 4px; padding: 4px;")
        self.mask_combo.currentIndexChanged.connect(self._on_mask_changed)
        layout.addWidget(self.mask_combo)

        self.mask_feather = SliderRow("Feather", 0.0, 0.5, 0.1, 0.5)
        self.mask_feather.value_changed.connect(lambda v: self._set_clip_attr("mask_feather", v))
        layout.addWidget(self.mask_feather)

        self.mask_inverted = QCheckBox("Invert Mask")
        self.mask_inverted.setStyleSheet("color: white; font-size: 12px;")
        self.mask_inverted.toggled.connect(lambda v: self._set_clip_attr("mask_inverted", v))
        layout.addWidget(self.mask_inverted)

        layout.addStretch()
        scroll.setWidget(container)
        outer = QVBoxLayout(w)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        return w

    def _build_chroma_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        chroma_label = QLabel("CHROMA KEY")
        chroma_label.setObjectName("sectionTitle")
        layout.addWidget(chroma_label)

        self.chroma_enable = QCheckBox("Enable Green Screen")
        self.chroma_enable.setStyleSheet("color: white; font-size: 12px;")
        self.chroma_enable.toggled.connect(lambda v: self._set_clip_attr("chroma_key_enabled", v))
        layout.addWidget(self.chroma_enable)

        preset_row = QHBoxLayout()
        preset_row.addWidget(QLabel("Preset"))
        self.chroma_preset = QComboBox()
        self.chroma_preset.addItems(["Green Screen", "Blue Screen", "Custom"])
        self.chroma_preset.setStyleSheet("background: #333; color: white; border: 1px solid #555; border-radius: 4px; padding: 3px;")
        self.chroma_preset.currentIndexChanged.connect(self._on_chroma_preset)
        preset_row.addWidget(self.chroma_preset)
        layout.addLayout(preset_row)

        self.chroma_tolerance_sl = SliderRow("Tolerance", 1.0, 80.0, 30.0, 79.0)
        self.chroma_tolerance_sl.value_changed.connect(lambda v: self._set_clip_attr("chroma_key_tolerance", v))
        layout.addWidget(self.chroma_tolerance_sl)

        self.chroma_hue_sl = SliderRow("Hue", 0.0, 180.0, 60.0, 180.0)
        self.chroma_hue_sl.value_changed.connect(lambda v: self._set_clip_attr("chroma_key_hue", v))
        layout.addWidget(self.chroma_hue_sl)

        layout.addStretch()
        return w

    def _reset_beauty(self):
        if not self.clip:
            return
        for attr, sl in self.sliders_beauty.items():
            sl.set_value(0.0)
            setattr(self.clip, attr, 0.0)
        if self.clip:
            self.clip_changed.emit(self.clip.id)

    def _on_lut_changed(self, idx: int):
        if self._updating or not self.clip:
            return
        self.clip.lut_id = self.lut_combo.itemData(idx) or ""
        self.clip_changed.emit(self.clip.id)

    def _on_mask_changed(self, idx: int):
        if self._updating or not self.clip:
            return
        self.clip.mask_type = self.mask_combo.itemData(idx) or ""
        self.clip_changed.emit(self.clip.id)

    def _on_chroma_preset(self, idx: int):
        if self._updating or not self.clip:
            return
        if idx == 0:  # Green
            self.clip.chroma_key_hue = 60.0
            self.chroma_hue_sl.set_value(60.0)
        elif idx == 1:  # Blue
            self.clip.chroma_key_hue = 120.0
            self.chroma_hue_sl.set_value(120.0)
        self.clip_changed.emit(self.clip.id)

    def _set_text_style(self, attr: str, value):
        if self._updating or not self.clip:
            return
        if hasattr(self.clip.text_style, attr):
            setattr(self.clip.text_style, attr, value)
            self.clip_changed.emit(self.clip.id)
