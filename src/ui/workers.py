"""Generic background worker: fn(*args, progress=cb, cancelled=cb) off the UI thread.
finished(result) always fires (None on cancel/error); error(msg) fires first on exceptions."""

from PyQt6.QtCore import QObject, QThread, pyqtSignal


class Worker(QObject):
    progress = pyqtSignal(int)
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, fn, *args):
        super().__init__()
        self._fn, self._args, self._cancel = fn, args, False

    def cancel(self):
        self._cancel = True

    def run(self):
        res = None
        try:
            res = self._fn(*self._args, progress=self.progress.emit, cancelled=lambda: self._cancel)
        except Exception as e:
            from src.ai.media import Cancelled
            if not isinstance(e, Cancelled):
                self.error.emit(str(e))
        self.finished.emit(res)


def start_worker(worker: Worker, parent):
    """Move worker to a parent-owned QThread and start it; returns the thread."""
    th = QThread(parent)
    worker.moveToThread(th)
    th.started.connect(worker.run)
    worker.finished.connect(th.quit)
    th.finished.connect(th.deleteLater)
    th.start()
    return th
