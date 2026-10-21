"""Speed-curve editor for the Speed & Motion tab."""

import math

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QComboBox, QPushButton, QLabel

from src.core.timemap import MIN_SPEED, MAX_SPEED

# name -> [[progress, speed], ...]  (own designs, not copied from any app)
PRESETS = {
    "Custom": None,
    "Montage": [[0, 0.5], [0.15, 2.0], [0.4, 0.6], [0.7, 2.5], [1, 1.0]],
    "Hero": [[0, 1.0], [0.3, 0.3], [0.6, 0.3], [0.8, 2.5], [1, 1.0]],
    "Bullet": [[0, 1.0], [0.25, 0.15], [0.55, 0.15], [0.75, 4.0], [1, 1.0]],
    "Jump Cut": [[0, 0.8], [0.25, 4.0], [0.5, 0.8], [0.75, 4.0], [1, 0.8]],
    "Flash In": [[0, 0.2], [0.35, 1.0], [1, 1.0]],
    "Flash Out": [[0, 1.0], [0.65, 1.0], [1, 0.2]],
}


class SpeedCurveEditor(QWidget):
    """Click = add point, drag = move, right-click = delete. Y axis is log 0.1x..10x."""
    changed = pyqtSignal(list)    # [] means "no curve" (constant speed)
    W, H = 240, 130

    def __init__(self, parent=None):
        super().__init__(parent)
        self._pts = []
        self._sel = -1
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        self._combo = QComboBox()
        self._combo.addItems(list(PRESETS))
        self._combo.activated.connect(self._on_preset)
        row.addWidget(self._combo, 1)
        rst = QPushButton("Reset")
        rst.clicked.connect(self.reset)
        row.addWidget(rst)
        lay.addLayout(row)
        self._area = QWidget()
        self._area.setFixedSize(self.W, self.H)
        self._area.paintEvent = self._paint
        self._area.mousePressEvent = self._press
        self._area.mouseMoveEvent = self._move
        self._area.mouseReleaseEvent = lambda e: setattr(self, '_sel', -1)
        lay.addWidget(self._area, 0, Qt.AlignmentFlag.AlignHCenter)
        self.info = QLabel("")
        self.info.setStyleSheet("color:#888;font-size:11px;")
        lay.addWidget(self.info)

    def curve(self):
        return [list(p) for p in self._pts] if len(self._pts) >= 2 else []

    def set_curve(self, curve):
        self._pts = sorted([float(a), float(b)] for a, b in (curve or []))
        self._combo.setCurrentIndex(0)
        self._area.update()

    def reset(self):
        self._pts = []
        self._combo.setCurrentIndex(0)
        self._emit()

    def _on_preset(self, _):
        pts = PRESETS[self._combo.currentText()]
        if pts:
            self._pts = [list(map(float, p)) for p in pts]
            self._emit()

    # speed <-> y (log scale)
    @staticmethod
    def _y(s):
        return 1 - (math.log10(s) - math.log10(MIN_SPEED)) / (math.log10(MAX_SPEED) - math.log10(MIN_SPEED))

    @staticmethod
    def _s(y):
        return 10 ** (math.log10(MIN_SPEED) + (1 - y) * (math.log10(MAX_SPEED) - math.log10(MIN_SPEED)))

    def _px(self, p):
        return QPointF(p[0] * self.W, self._y(p[1]) * self.H)

    def _pt(self, q):
        return [min(1.0, max(0.0, q.x() / self.W)),
                min(MAX_SPEED, max(MIN_SPEED, self._s(min(1.0, max(0.0, q.y() / self.H)))))]

    def _hit(self, q):
        for i, p in enumerate(self._pts):
            d = self._px(p) - q
            if math.hypot(d.x(), d.y()) < 9:
                return i
        return -1

    def _press(self, e):
        i = self._hit(e.position())
        if e.button() == Qt.MouseButton.RightButton:
            if i >= 0 and len(self._pts) > 2:
                del self._pts[i]
                self._emit()
            return
        if not self._pts:       # first edit: start from flat 1x with both ends
            self._pts = [[0.0, 1.0], [1.0, 1.0]]
        if i < 0:
            self._pts.append(self._pt(e.position()))
            self._pts.sort()
            i = self._hit(e.position())
            self._emit()
        self._sel = i

    def _move(self, e):
        i = self._sel
        if i < 0:
            return
        x, y = self._pt(e.position())
        pts = self._pts
        if i in (0, len(pts) - 1):
            x = pts[i][0]
        else:
            x = min(pts[i + 1][0] - 0.01, max(pts[i - 1][0] + 0.01, x))
        pts[i] = [x, y]
        self._combo.setCurrentIndex(0)
        self._emit()

    def _emit(self):
        self._area.update()
        self.changed.emit(self.curve())

    def set_info(self, text):
        self.info.setText(text)

    def _paint(self, _):
        p = QPainter(self._area)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(0, 0, self.W, self.H, QColor('#1c1c1c'))
        p.setPen(QPen(QColor('#333'), 1))
        for i in range(1, 4):
            p.drawLine(i * self.W // 4, 0, i * self.W // 4, self.H)
        for s in (0.25, 0.5, 2, 4):
            y = self._y(s) * self.H
            p.drawLine(0, int(y), self.W, int(y))
        p.setPen(QPen(QColor('#777'), 1, Qt.PenStyle.DashLine))   # 1x reference
        y1 = int(self._y(1.0) * self.H)
        p.drawLine(0, y1, self.W, y1)
        if len(self._pts) >= 2:
            from src.core.grading import _pchip
            xs = np.array([q[0] for q in self._pts])
            ys = np.array([q[1] for q in self._pts])
            gx = np.linspace(0, 1, 80)
            gy = np.clip(_pchip(xs, ys, gx), MIN_SPEED, MAX_SPEED)
            p.setPen(QPen(QColor('#fe2c55'), 2))
            for a in range(79):
                p.drawLine(self._px([gx[a], gy[a]]), self._px([gx[a + 1], gy[a + 1]]))
            p.setBrush(QColor('#fe2c55'))
            p.setPen(Qt.PenStyle.NoPen)
            for q in self._pts:
                p.drawEllipse(self._px(q), 4, 4)
        p.setPen(QColor('#666'))
        p.drawText(3, 11, "10x")
        p.drawText(3, self.H - 3, "0.1x")
        p.end()


from PyQt6.QtCore import QObject, QThread


class StabilizeWorker(QObject):
    """Runs core.stabilize.analyze off the UI thread (own VideoCapture: not thread-safe to share)."""
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)      # stabilize dict or None (cancelled/failed)

    def __init__(self, path, start_ms, end_ms, level):
        super().__init__()
        self.args = (path, start_ms, end_ms, level)
        self._cancel = False

    def cancel(self):
        self._cancel = True

    def run(self):
        try:
            from src.core import stabilize
            res = stabilize.analyze(*self.args, progress=self.progress.emit, cancelled=lambda: self._cancel)
        except Exception:
            res = None
        self.finished.emit(res)


def start_worker(worker: StabilizeWorker, parent):
    """Move worker to a QThread owned by parent; returns the thread."""
    th = QThread(parent)
    worker.moveToThread(th)
    th.started.connect(worker.run)
    worker.finished.connect(th.quit)
    th.finished.connect(th.deleteLater)
    th.start()
    return th
