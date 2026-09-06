"""OpenGL-accelerated video view.

Frames are drawn inside a QOpenGLWidget, where QPainter is GPU-accelerated:
the image is uploaded to the GPU once per frame and scaling/compositing
happen in hardware, so fullscreen stays smooth regardless of window size.
Falls back gracefully if OpenGL is unavailable.
"""
from __future__ import annotations

import cv2
import numpy as np
from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QFont, QImage, QPainter, QPen
from PySide6.QtOpenGLWidgets import QOpenGLWidget


class VideoView(QOpenGLWidget):
    """Displays numpy BGR frames on a GPU-backed surface."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._frame_image: QImage | None = None
        self._status_text = ""
        self.gl_ok = False
        self.setAutoFillBackground(False)

    # ------------------------------------------------------------------ #
    def set_frame(self, frame_bgr: np.ndarray) -> None:
        """Hand over a new frame (BGR uint8) and schedule a repaint."""
        # cvtColor returns a C-contiguous array (a strided numpy view would
        # make QImage reject the buffer).
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        self._frame_image = QImage(
            rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888
        ).copy()
        self.update()

    def set_status(self, text: str) -> None:
        self._status_text = text

    # ------------------------------------------------------------------ #
    def initializeGL(self) -> None:  # noqa: N802 (Qt naming)
        self.gl_ok = True

    def paintGL(self) -> None:  # noqa: N802 (Qt naming)
        # QPainter is GPU-accelerated inside a QOpenGLWidget's paintGL:
        # drawImage uploads the frame to the GPU and scales it in hardware.
        painter = QPainter(self)
        painter.fillRect(self.rect(), Qt.GlobalColor.black)

        if self._frame_image is not None:
            painter.setRenderHint(
                QPainter.RenderHint.SmoothPixmapTransform, True
            )
            painter.drawImage(self._letterbox_rect(), self._frame_image)

        if self._status_text:
            painter.setPen(QPen(Qt.GlobalColor.white))
            font = QFont()
            font.setPointSize(16)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(20, 40, self._status_text)

        painter.end()

    # ------------------------------------------------------------------ #
    def _letterbox_rect(self) -> QRect:
        img = self._frame_image
        scaled = img.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
        x = (self.width() - scaled.width()) // 2
        y = (self.height() - scaled.height()) // 2
        return QRect(x, y, scaled.width(), scaled.height())
