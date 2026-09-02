"""Application settings with JSON persistence."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = PROJECT_ROOT / "settings.json"


@dataclass
class AppSettings:
    """All user-adjustable settings of the installation."""

    camera_index: int = 0
    framerate: int = 30
    exposure_auto: bool = True
    # Raw exposure value. Meaning depends on the capture backend:
    # Windows/DirectShow: log2(seconds), e.g. -6 == 1/64 s.
    # Linux/V4L2: driver dependent, often absolute (e.g. 1/10000 s units).
    exposure: float = -6.0
    record_interval: float = 30.0  # seconds of light-painting per round
    hold_interval: float = 10.0    # seconds the finished painting is shown
    save_enabled: bool = True
    save_folder: str = "paintings"  # relative to project root or absolute
    threshold: int = 30            # min. brightness (0-255) for a pixel to be recorded
    mirror: bool = True            # horizontal mirror (visitors face the camera)
    blend_mode: str = "maximum"    # "maximum" | "add" | "screen"

    def save_dir(self) -> Path:
        """Resolve the save folder to an absolute path."""
        folder = Path(self.save_folder)
        if not folder.is_absolute():
            folder = PROJECT_ROOT / folder
        return folder


def load_settings(path: Path = SETTINGS_FILE) -> AppSettings:
    """Load settings from JSON, falling back to defaults for unknown/missing keys."""
    settings = AppSettings()
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            valid = {k: v for k, v in data.items() if k in asdict(settings)}
            settings = AppSettings(**valid)
        except (json.JSONDecodeError, TypeError) as exc:
            print(f"Warning: could not parse {path}: {exc}. Using defaults.")
    return settings


def save_settings(settings: AppSettings, path: Path = SETTINGS_FILE) -> None:
    """Persist settings to JSON."""
    path.write_text(json.dumps(asdict(settings), indent=2), encoding="utf-8")
