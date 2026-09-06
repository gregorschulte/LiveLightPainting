"""Headless smoke test for the LiveLightPainting pipeline.

Verifies (without a webcam or display):
1. PaintingEngine: threshold masking, accumulation, RECORDING -> HOLD -> reset.
2. Full GUI in --demo mode (offscreen Qt): a round completes and the
   finished painting is saved to disk.

Run:  python smoke_test.py
"""
from __future__ import annotations

import glob
import os
import sys
import tempfile
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cv2
import numpy as np

from app.painting_engine import EngineState, PaintingEngine
from app.settings import AppSettings


def test_engine() -> None:
    settings = AppSettings(
        record_interval=0.5, hold_interval=0.5, threshold=50, mirror=False
    )
    engine = PaintingEngine(settings)

    dark = np.zeros((100, 100, 3), dtype=np.uint8)
    bright = dark.copy()
    bright[10, 10] = (255, 255, 255)
    dim = dark.copy()
    dim[20, 20] = (30, 30, 30)  # below threshold -> must be ignored

    engine.update(dark)
    engine.update(bright)
    engine.update(dim)

    assert engine._accumulator[10, 10].max() == 255, "bright pixel not recorded"
    assert engine._accumulator[20, 20].max() == 0, "dim pixel passed threshold"

    time.sleep(0.6)
    result = engine.update(dark)
    assert result.state is EngineState.HOLD, "round did not finish in time"
    assert result.finished_image is not None, "no finished image emitted"
    assert result.finished_image[10, 10].max() == 255

    time.sleep(0.6)
    result = engine.update(dark)
    assert result.state is EngineState.RECORDING, "did not return to RECORDING"
    # After the reset the accumulator is either cleared or lazily recreated.
    assert engine._accumulator is None or engine._accumulator.max() == 0, (
        "accumulator was not reset for the next round"
    )
    print("engine tests OK")


def test_gui_demo(app) -> None:
    from PySide6.QtCore import QTimer

    from app.main_window import MainWindow

    tmp = tempfile.mkdtemp(prefix="llp_test_")
    settings = AppSettings(
        record_interval=1.5,
        hold_interval=1.0,
        save_enabled=True,
        save_folder=tmp,
        framerate=20,
        threshold=50,
    )
    window = MainWindow(settings, demo=True)
    window.show()
    QTimer.singleShot(6000, app.quit)  # run ~2 full rounds, then quit
    app.exec()

    files = glob.glob(os.path.join(tmp, "painting_*.png"))
    assert files, "no painting was saved to disk"
    image = cv2.imread(files[0])
    assert image is not None and image.max() > 200, (
        "saved painting is empty or unreadable"
    )
    print(f"GUI smoke test OK - saved painting: {files[0]}")
    window.close()
    window.worker.wait(2000)


def test_render_performance(app) -> None:
    """Frame hand-off to the view must stay well within a frame budget."""
    from app.main_window import MainWindow

    window = MainWindow(AppSettings(), demo=True)
    window.show()
    window.resize(1920, 1080)  # simulate fullscreen
    window.worker.stop()
    window.worker.wait(2000)

    frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
    window._show_frame(frame, "test")  # warm-up (GL init happens here)
    start = time.perf_counter()
    for _ in range(30):
        window._show_frame(frame, "test")
    per_frame_ms = (time.perf_counter() - start) / 30 * 1000
    assert per_frame_ms < 33, f"rendering too slow: {per_frame_ms:.1f} ms/frame"
    mode = "OpenGL" if window._use_gl else "software fallback"
    print(f"render performance OK - {per_frame_ms:.1f} ms/frame ({mode})")
    window.close()


def test_settings_dialog_opens_instantly(app) -> None:
    """Constructing the dialog must not block on camera enumeration."""
    from app.settings_dialog import SettingsDialog

    start = time.perf_counter()
    dialog = SettingsDialog(AppSettings())
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"dialog blocked for {elapsed:.2f} s"
    dialog.apply_to(AppSettings())  # must not crash while scan is running
    dialog._scanner.wait(5000)
    dialog.close()
    print(f"settings dialog OK - constructed in {elapsed * 1000:.0f} ms")


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    test_engine()
    app = QApplication([])  # one QApplication shared by all GUI tests
    test_gui_demo(app)
    test_render_performance(app)
    test_settings_dialog_opens_instantly(app)
    print("All smoke tests passed.")
