"""Color wheel + curve editor widgets for the Grade tab."""

import colorsys
import math

from PyQt6.QtCore import Qt, pyqtSignal, QPointF, QRectF
from PyQt6.QtGui import QColor, QConicalGradient, QRadialGradient, QPainter, QPen, QBrush
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider, QComboBox, QPushButton


class ColorWheel(QWidget):
    """Hue/sat puck -> [r, g, b] offsets (+ master slider). value() = [r, g, b, master]."""
    changed = pyqtSignal(list)

    def __init__(self, title: str, scale: float, parent=None):
        super().__init__(parent)
        self._k = scale          # max per-channel offset at the rim
        self._pos = QPointF(0, 0)   # unit disc
        self._master = 0.0
        self._drag = False
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(2)
        lbl = QLabel(title)
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet("color:#aaa;font-size:11px;background:transparent;")
        lay.addWidget(lbl)
        self._disc = QWidget()
        self._disc.setFixedSize(96, 96)
        self._disc.paintEvent = self._paint
        self._disc.mousePressEvent = self._press
        self._disc.mouseMoveEvent = self._move
        self._disc.mouseReleaseEvent = lambda e: setattr(self, '_drag', False)
        self._disc.mouseDoubleClickEvent = lambda e: self.reset()
        lay.addWidget(self._disc, 0, Qt.AlignmentFlag.AlignHCenter)
        self._sl = QSlider(Qt.Orientation.Horizontal)
        self._sl.setRange(-100, 100)
        self._sl.valueChanged.connect(self._on_master)
        lay.addWidget(self._sl)

    # value <-> puck
    def value(self):
        r = math.hypot(self._pos.x(), self._pos.y())
        if r < 1e-6:
            return [0.0, 0.0, 0.0, self._master]
        hue = (math.degrees(math.atan2(-self._pos.y(), self._pos.x())) % 360) / 360
        rgb = colorsys.hsv_to_rgb(hue, 1, 1)
        m = sum(rgb) / 3
        return [(c - m) * r * self._k * 1.5 for c in rgb] + [self._master]

    def set_value(self, v):
        v = (list(v or []) + [0.0] * 4)[:4]
        self._master = v[3]
        self._sl.blockSignals(True)
        self._sl.setValue(int(v[3] / self._k * 100))
        self._sl.blockSignals(False)
        c = [x - min(v[:3]) for x in v[:3]]
        mx = max(c)
        if mx < 1e-6:
            self._pos = QPointF(0, 0)
        else:
            h = colorsys.rgb_to_hsv(*[x / mx for x in c])[0] * 2 * math.pi
            r = min(1.0, mx / (self._k * 1.5))
            self._pos = QPointF(r * math.cos(h), -r * math.sin(h))
        self._disc.update()

    def reset(self):
        self.set_value([0, 0, 0, 0])
        self.changed.emit(self.value())

    def _on_master(self, v):
        self._master = v / 100 * self._k
        self.changed.emit(self.value())

    def _set_from_mouse(self, p):
        c = self._disc.width() / 2
        x, y = (p.x() - c) / (c - 4), (p.y() - c) / (c - 4)
        n = math.hypot(x, y)
        if n > 1:
            x, y = x / n, y / n
        self._pos = QPointF(x, y)
        self._disc.update()
        self.changed.emit(self.value())

    def _press(self, e):
        self._drag = True
        self._set_from_mouse(e.position())

    def _move(self, e):
        if self._drag:
            self._set_from_mouse(e.position())

    def _paint(self, _):
        p = QPainter(self._disc)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        c = self._disc.width() / 2
        rect = QRectF(4, 4, 2 * c - 8, 2 * c - 8)
        g = QConicalGradient(QPointF(c, c), 0)
        for i in range(7):
            g.setColorAt(i / 6, QColor.fromHsvF((i % 6) / 6, 1, 1))
        p.setBrush(QBrush(g))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawEllipse(rect)
        rg = QRadialGradient(QPointF(c, c), c - 4)
        rg.setColorAt(0, QColor(128, 128, 128, 255))
        rg.setColorAt(1, QColor(128, 128, 128, 0))
        p.setBrush(QBrush(rg))
        p.drawEllipse(rect)
        px, py = c + self._pos.x() * (c - 4), c + self._pos.y() * (c - 4)
        p.setPen(QPen(QColor('white'), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(px, py), 5, 5)
        p.end()


class CurveEditor(QWidget):
    """Master/R/G/B curve editor. Click = add point, drag = move, right-click = delete."""
    changed = pyqtSignal(dict)
    KEYS = ['master', 'r', 'g', 'b']
    COLORS = {'master': '#dddddd', 'r': '#ff5050', 'g': '#50e050', 'b': '#5090ff'}
    SIZE = 180

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pts = {k: [[0.0, 0.0], [1.0, 1.0]] for k in self.KEYS}
        self._key = 'master'
        self._sel = -1
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        self._combo = QComboBox()
        for k, n in zip(self.KEYS, ['Master', 'Red', 'Green', 'Blue']):
            self._combo.addItem(n, k)
        self._combo.currentIndexChanged.connect(self._on_key)
        row.addWidget(self._combo, 1)
        rst = QPushButton("Reset")
        rst.clicked.connect(self.reset)
        row.addWidget(rst)
        lay.addLayout(row)
        self._area = QWidget()
        self._area.setFixedSize(self.SIZE, self.SIZE)
        self._area.paintEvent = self._paint
        self._area.mousePressEvent = self._press
        self._area.mouseMoveEvent = self._move
        self._area.mouseReleaseEvent = lambda e: setattr(self, '_sel', -1)
        lay.addWidget(self._area, 0, Qt.AlignmentFlag.AlignHCenter)

    def curves(self) -> dict:
        """Only non-identity channels."""
        return {k: [list(p) for p in v] for k, v in self._pts.items()
                if any(abs(p[0] - p[1]) > 1e-4 for p in v)}

    def set_curves(self, curves):
        curves = curves or {}
        for k in self.KEYS:
            pts = curves.get(k) or [[0.0, 0.0], [1.0, 1.0]]
            self._pts[k] = sorted([[float(a), float(b)] for a, b in pts])
        self._area.update()

    def reset(self):
        self.set_curves({})
        self.changed.emit(self.curves())

    def _on_key(self, _):
        self._key = self._combo.currentData()
        self._area.update()

    def _to_px(self, p):
        s = self.SIZE
        return QPointF(p[0] * s, (1 - p[1]) * s)

    def _from_px(self, q):
        s = self.SIZE
        return [min(1, max(0, q.x() / s)), min(1, max(0, 1 - q.y() / s))]

    def _hit(self, q):
        for i, p in enumerate(self._pts[self._key]):
            d = self._to_px(p) - q
            if math.hypot(d.x(), d.y()) < 9:
                return i
        return -1

    def _press(self, e):
        pts = self._pts[self._key]
        i = self._hit(e.position())
        if e.button() == Qt.MouseButton.RightButton:
            if 0 < i < len(pts) - 1:
                del pts[i]
                self._emit()
            return
        if i < 0:
            pts.append(self._from_px(e.position()))
            pts.sort()
            i = self._hit(e.position())
        self._sel = i
        self._area.update()

    def _move(self, e):
        pts = self._pts[self._key]
        i = self._sel
        if i < 0:
            return
        x, y = self._from_px(e.position())
        if i == 0 or i == len(pts) - 1:
            x = pts[i][0]                       # endpoints slide vertically only
        else:
            x = min(pts[i + 1][0] - 0.01, max(pts[i - 1][0] + 0.01, x))
        pts[i] = [x, y]
        self._emit()

    def _emit(self):
        self._area.update()
        self.changed.emit(self.curves())

    def _paint(self, _):
        p = QPainter(self._area)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        s = self.SIZE
        p.fillRect(0, 0, s, s, QColor('#1c1c1c'))
        p.setPen(QPen(QColor('#333'), 1))
        for i in range(1, 4):
            p.drawLine(i * s // 4, 0, i * s // 4, s)
            p.drawLine(0, i * s // 4, s, i * s // 4)
        p.setPen(QPen(QColor('#444'), 1))
        p.drawLine(0, s, s, 0)
        col = QColor(self.COLORS[self._key])
        pts = self._pts[self._key]
        if len(pts) >= 2:
            from src.core.grading import _pchip
            import numpy as np
            xs = np.array([q[0] for q in pts])
            ys = np.array([q[1] for q in pts])
            gx = np.linspace(0, 1, 64)
            gy = _pchip(xs, ys, gx)
            p.setPen(QPen(col, 2))
            for a, b in zip(range(63), range(1, 64)):
                p.drawLine(self._to_px([gx[a], gy[a]]), self._to_px([gx[b], gy[b]]))
        p.setBrush(col)
        p.setPen(Qt.PenStyle.NoPen)
        for q in pts:
            p.drawEllipse(self._to_px(q), 4, 4)
        p.end()
