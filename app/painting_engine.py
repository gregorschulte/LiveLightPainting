"""Light-painting accumulation engine and round state machine.

The engine emulates a long exposure digitally: every frame is merged into an
accumulator so that bright elements "burn into" the image while dark regions
stay dark. A brightness threshold suppresses sensor noise and ambient light.

Round cycle (fully automatic):
    RECORDING (record_interval) -> HOLD (hold_interval) -> reset -> RECORDING ...
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum, auto
from typing import Optional

import cv2
import numpy as np

from .settings import AppSettings


class EngineState(Enum):
    RECORDING = auto()
    HOLD = auto()


@dataclass
class EngineResult:
    display: np.ndarray              # image to show right now
    state: EngineState
    progress: float                  # 0..1 progress of the current phase
    remaining: float                 # seconds left in the current phase
    finished_image: Optional[np.ndarray] = None  # set once when a round ends


class PaintingEngine:
    """Accumulates frames into a light painting and manages round timing."""

    def __init__(self, settings: AppSettings) -> None:
        self.settings = settings
        self.state = EngineState.RECORDING
        self._accumulator: Optional[np.ndarray] = None
        self._finished: Optional[np.ndarray] = None
        self._record_start = time.monotonic()
        self._hold_start: Optional[float] = None

    def reset(self) -> None:
        """Discard the current painting and start a fresh round."""
        self._accumulator = None
        self._finished = None
        self.state = EngineState.RECORDING
        self._record_start = time.monotonic()
        self._hold_start = None

    def update(self, frame: np.ndarray) -> EngineResult:
        """Feed one camera frame; returns what to display plus round status."""
        now = time.monotonic()
        if self.settings.mirror:
            frame = cv2.flip(frame, 1)
        if self._accumulator is None:
            self._accumulator = np.zeros_like(frame)

        finished_image: Optional[np.ndarray] = None

        if self.state is EngineState.RECORDING:
            self._accumulate(frame)
            elapsed = now - self._record_start
            progress = min(1.0, elapsed / max(0.001, self.settings.record_interval))
            remaining = max(0.0, self.settings.record_interval - elapsed)
            display = self._accumulator
            if elapsed >= self.settings.record_interval:
                self.state = EngineState.HOLD
                self._hold_start = now
                self._finished = self._accumulator.copy()
                finished_image = self._finished
                progress = 1.0
                remaining = self.settings.hold_interval
        else:  # HOLD
            held = now - (self._hold_start or now)
            progress = min(1.0, held / max(0.001, self.settings.hold_interval))
            remaining = max(0.0, self.settings.hold_interval - held)
            display = self._finished if self._finished is not None else self._accumulator
            if held >= self.settings.hold_interval:
                self.reset()

        return EngineResult(
            display=display,
            state=self.state,
            progress=progress,
            remaining=remaining,
            finished_image=finished_image,
        )

    def _accumulate(self, frame: np.ndarray) -> None:
        """Merge the bright parts of *frame* into the accumulator."""
        assert self._accumulator is not None
        # Per-pixel brightness = strongest colour channel.
        brightness = frame.max(axis=2)
        mask = brightness >= self.settings.threshold

        mode = self.settings.blend_mode
        if mode == "add":
            blended = cv2.add(self._accumulator, frame)  # saturating add
        elif mode == "screen":
            a = self._accumulator.astype(np.float32)
            f = frame.astype(np.float32)
            blended = (255.0 - (255.0 - a) * (255.0 - f) / 255.0).astype(np.uint8)
        else:  # "maximum" - classic long-exposure look
            blended = np.maximum(self._accumulator, frame)

        # Only pixels above the threshold are allowed to draw.
        self._accumulator[mask] = blended[mask]
