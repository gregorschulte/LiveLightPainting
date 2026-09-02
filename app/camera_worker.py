"""Camera capture running in its own thread, plus a synthetic demo source."""
from __future__ import annotations

import math
import platform
import time

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

from .settings import AppSettings

DEMO_WIDTH, DEMO_HEIGHT = 1280, 720


def capture_backend() -> int:
    """Pick the best OpenCV capture backend for the current OS."""
    return cv2.CAP_DSHOW if platform.system() == "Windows" else cv2.CAP_V4L2


def enumerate_cameras(max_index: int = 5) -> list[int]:
    """Probe device indices and return the ones that can be opened."""
    found: list[int] = []
    for index in range(max_index + 1):
        cap = cv2.VideoCapture(index, capture_backend())
        if cap.isOpened():
            found.append(index)
        cap.release()
    return found


class CameraWorker(QThread):
    """Continuously grabs frames and emits them as `frame_ready(np.ndarray)`."""

    frame_ready = Signal(object)
    error = Signal(str)

    def __init__(self, settings: AppSettings, demo: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.demo = demo
        self._running = True

    def stop(self) -> None:
        self._running = False

    # ------------------------------------------------------------------ #
    def run(self) -> None:
        if self.demo:
            self._run_demo()
        else:
            self._run_camera()

    # ------------------------------------------------------------------ #
    def _run_camera(self) -> None:
        s = self.settings
        cap = cv2.VideoCapture(s.camera_index, capture_backend())
        if not cap.isOpened():
            self.error.emit(f"Could not open camera {s.camera_index}.")
            return

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, DEMO_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DEMO_HEIGHT)
        cap.set(cv2.CAP_PROP_FPS, s.framerate)

        # Auto-exposure flag semantics differ per backend (driver quirk).
        if platform.system() == "Windows":
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.75 if s.exposure_auto else 0.25)
        else:
            cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 3 if s.exposure_auto else 1)
        if not s.exposure_auto:
            cap.set(cv2.CAP_PROP_EXPOSURE, s.exposure)

        while self._running:
            ok, frame = cap.read()
            if ok:
                self.frame_ready.emit(frame)
            else:
                time.sleep(0.05)
        cap.release()

    # ------------------------------------------------------------------ #
    def _run_demo(self) -> None:
        """Synthetic source: a bright dot moving on a Lissajous curve in a
        dark room - lets you test the whole pipeline without a webcam."""
        fps = max(1, self.settings.framerate)
        period = 1.0 / fps
        t = 0.0
        while self._running:
            frame = np.zeros((DEMO_HEIGHT, DEMO_WIDTH, 3), dtype=np.uint8)
            # faint background noise
            noise = np.random.randint(0, 15, frame.shape, dtype=np.uint8)
            frame = cv2.add(frame, noise)
            x = int(DEMO_WIDTH / 2 + (DEMO_WIDTH * 0.4) * math.sin(t * 1.3))
            y = int(DEMO_HEIGHT / 2 + (DEMO_HEIGHT * 0.4) * math.sin(t * 2.1))
            cv2.circle(frame, (x, y), 12, (255, 255, 255), -1)
            cv2.circle(frame, (x, y), 22, (120, 180, 255), 4)
            self.frame_ready.emit(frame)
            t += period
            time.sleep(period)
