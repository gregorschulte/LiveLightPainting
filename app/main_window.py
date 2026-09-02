"""Main exhibition window: live painting view + progress bar + hotkeys."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QImage, QKeyEvent, QPixmap
from PySide6.QtWidgets import QLabel, QMainWindow, QProgressBar, QVBoxLayout, QWidget

from .camera_worker import CameraWorker
from .painting_engine import EngineState, PaintingEngine
from .settings import AppSettings, save_settings
from .settings_dialog import SettingsDialog


class MainWindow(QMainWindow):
    def __init__(self, settings: AppSettings, demo: bool = False) -> None:
        super().__init__()
        self.settings = settings
        self.demo = demo
        self.setWindowTitle("LiveLightPainting")

        # --- UI ----------------------------------------------------------
        self.video_label = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self.video_label.setMinimumSize(640, 360)
        self.video_label.setStyleSheet("background-color: black;")

        self.progress = QProgressBar()
        self.progress.setTextVisible(True)
        self.progress.setFixedHeight(24)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.video_label, stretch=1)
        layout.addWidget(self.progress)

        central = QWidget()
        central.setLayout(layout)
        self.setCentralWidget(central)
        self.resize(1280, 800)

        # --- engine + camera ---------------------------------------------
        self.engine = PaintingEngine(settings)
        self.worker: CameraWorker | None = None
        self._start_worker()

    # ------------------------------------------------------------------ #
    def _start_worker(self) -> None:
        if self.worker is not None:
            self.worker.stop()
            self.worker.wait(2000)
        self.worker = CameraWorker(self.settings, demo=self.demo)
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.error.connect(lambda msg: print(f"Camera error: {msg}"))
        self.worker.start()

    # ------------------------------------------------------------------ #
    @Slot(object)
    def _on_frame(self, frame: np.ndarray) -> None:
        result = self.engine.update(frame)

        if result.finished_image is not None:
            self._save_painting(result.finished_image)

        display = result.display.copy()
        if result.state is EngineState.RECORDING:
            status = f"Painting... {result.remaining:.0f} s"
            total = self.settings.record_interval
        else:
            status = f"Finished - next round in {result.remaining:.0f} s"
            total = self.settings.hold_interval

        cv2.putText(
            display, status, (16, 40),
            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA,
        )
        self.progress.setMaximum(max(1, int(total * 10)))
        self.progress.setValue(int(result.progress * total * 10))
        self.progress.setFormat(status)

        self._show_frame(display)

    def _show_frame(self, frame: np.ndarray) -> None:
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, _ = rgb.shape
        image = QImage(rgb.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(image.copy())
        self.video_label.setPixmap(
            pixmap.scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def _save_painting(self, image: np.ndarray) -> None:
        if not self.settings.save_enabled:
            return
        folder = self.settings.save_dir()
        folder.mkdir(parents=True, exist_ok=True)
        name = f"painting_{datetime.now():%Y-%m-%d_%H-%M-%S}.png"
        path = folder / name
        if cv2.imwrite(str(path), image):
            print(f"Saved painting: {path}")
        else:
            print(f"Failed to save painting: {path}")

    # ------------------------------------------------------------------ #
    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self.close()
        elif key == Qt.Key.Key_F:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        elif key == Qt.Key.Key_S:
            self._open_settings()
        elif key == Qt.Key.Key_Space:
            self.engine.reset()
        else:
            super().keyPressEvent(event)

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, parent=self)
        if dialog.exec():
            camera_changed = (
                dialog.camera_combo.currentData() != self.settings.camera_index
                or dialog.fps_spin.value() != self.settings.framerate
                or dialog.exposure_auto_check.isChecked() != self.settings.exposure_auto
                or dialog.exposure_spin.value() != self.settings.exposure
            )
            dialog.apply_to(self.settings)
            save_settings(self.settings)
            self.engine.reset()
            if camera_changed or self.demo:
                self._start_worker()

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        if self.worker is not None:
            self.worker.stop()
            self.worker.wait(2000)
        super().closeEvent(event)
