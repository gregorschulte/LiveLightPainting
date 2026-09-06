"""LiveLightPainting - interactive light-painting installation.

Usage:
    python main.py              # run with webcam
    python main.py --demo       # synthetic moving light, no webcam needed
    python main.py --fullscreen # start in fullscreen (exhibition mode)
"""
from __future__ import annotations

import argparse
import sys

from PySide6.QtGui import QSurfaceFormat
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow
from app.settings import load_settings


def main() -> int:
    parser = argparse.ArgumentParser(description="LiveLightPainting installation")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="use a synthetic moving-light source instead of a webcam",
    )
    parser.add_argument(
        "--fullscreen",
        action="store_true",
        help="start in fullscreen mode",
    )
    args = parser.parse_args()

    settings = load_settings()

    # Request a vsynced GL surface before creating the app.
    # (Qt6 surfaces are always double-buffered; there is no setDoubleBuffer.)
    fmt = QSurfaceFormat()
    fmt.setSwapInterval(1)  # vsync - smooth, tear-free fullscreen
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)
    window = MainWindow(settings, demo=args.demo)
    if args.fullscreen:
        window.showFullScreen()
    else:
        window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
