"""Settings dialog: camera, framerate, exposure, intervals, threshold, saving."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from .camera_worker import CameraScanThread
from .settings import AppSettings

BLEND_MODES = ["maximum", "add", "screen"]


class SettingsDialog(QDialog):
    """Modal dialog to edit an AppSettings instance."""

    def __init__(self, settings: AppSettings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("Settings")
        self.setMinimumWidth(420)

        form = QFormLayout()

        # --- camera selection -------------------------------------------
        # Probing cameras can take seconds (and may block while a camera is
        # in use), so it runs in a background thread; the dialog opens
        # instantly with the currently configured camera pre-selected.
        self.camera_combo = QComboBox()
        self.camera_combo.addItem(
            f"Camera {settings.camera_index}", userData=settings.camera_index
        )
        self.camera_combo.addItem("Scanning…", userData=None)
        self._scanner = CameraScanThread(self)
        self._scanner.finished_scan.connect(self._on_cameras_scanned)
        self._scanner.start()
        form.addRow("Webcam", self.camera_combo)

        # --- framerate ---------------------------------------------------
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(1, 60)
        self.fps_spin.setSuffix(" fps")
        self.fps_spin.setValue(settings.framerate)
        form.addRow("Framerate", self.fps_spin)

        # --- exposure ----------------------------------------------------
        self.exposure_auto_check = QCheckBox("Automatic exposure")
        self.exposure_auto_check.setChecked(settings.exposure_auto)
        form.addRow("Exposure", self.exposure_auto_check)

        self.exposure_spin = QDoubleSpinBox()
        self.exposure_spin.setRange(-13.0, 13.0)
        self.exposure_spin.setSingleStep(0.5)
        self.exposure_spin.setValue(settings.exposure)
        self.exposure_spin.setEnabled(not settings.exposure_auto)
        self.exposure_spin.setToolTip(
            "Raw exposure value (driver dependent).\n"
            "Windows/DirectShow: log2(seconds), e.g. -6 = 1/64 s.\n"
            "Lower value = darker/shorter exposure."
        )
        self.exposure_auto_check.toggled.connect(
            lambda auto: self.exposure_spin.setEnabled(not auto)
        )
        form.addRow("Exposure value", self.exposure_spin)

        # --- intervals ---------------------------------------------------
        self.record_spin = QDoubleSpinBox()
        self.record_spin.setRange(5.0, 600.0)
        self.record_spin.setSuffix(" s")
        self.record_spin.setValue(settings.record_interval)
        form.addRow("Recording interval", self.record_spin)

        self.hold_spin = QDoubleSpinBox()
        self.hold_spin.setRange(2.0, 300.0)
        self.hold_spin.setSuffix(" s")
        self.hold_spin.setValue(settings.hold_interval)
        form.addRow("Hold interval", self.hold_spin)

        # --- brightness threshold ----------------------------------------
        threshold_row = QHBoxLayout()
        self.threshold_slider = QSlider(Qt.Orientation.Horizontal)
        self.threshold_slider.setRange(0, 255)
        self.threshold_slider.setValue(settings.threshold)
        self.threshold_label = QLabel(str(settings.threshold))
        self.threshold_slider.valueChanged.connect(
            lambda v: self.threshold_label.setText(str(v))
        )
        self.threshold_slider.setToolTip(
            "Minimum brightness a pixel needs to be recorded.\n"
            "Raise it to suppress sensor noise and ambient light."
        )
        threshold_row.addWidget(self.threshold_slider, stretch=1)
        threshold_row.addWidget(self.threshold_label)
        form.addRow("Brightness threshold", threshold_row)

        # --- extras -------------------------------------------------------
        self.blend_combo = QComboBox()
        self.blend_combo.addItems(BLEND_MODES)
        self.blend_combo.setCurrentText(settings.blend_mode)
        form.addRow("Blend mode", self.blend_combo)

        self.mirror_check = QCheckBox("Mirror image horizontally")
        self.mirror_check.setChecked(settings.mirror)
        form.addRow("Mirror", self.mirror_check)

        # --- saving --------------------------------------------------------
        self.save_check = QCheckBox("Save finished paintings to disk")
        self.save_check.setChecked(settings.save_enabled)
        form.addRow("Save", self.save_check)

        folder_row = QHBoxLayout()
        self.folder_edit = QLineEdit(settings.save_folder)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_folder)
        folder_row.addWidget(self.folder_edit, stretch=1)
        folder_row.addWidget(browse_btn)
        form.addRow("Save folder", folder_row)

        # --- buttons --------------------------------------------------------
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    # ------------------------------------------------------------------ #
    def _on_cameras_scanned(self, cameras: list[int]) -> None:
        """Populate the webcam dropdown once the background scan finished."""
        current = self.settings.camera_index
        if current not in cameras:
            cameras = sorted(cameras + [current])
        self.camera_combo.clear()
        for index in cameras:
            self.camera_combo.addItem(f"Camera {index}", userData=index)
        self.camera_combo.setCurrentIndex(self.camera_combo.findData(current))

    def _browse_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select save folder")
        if folder:
            self.folder_edit.setText(folder)

    def apply_to(self, settings: AppSettings) -> None:
        """Write the dialog values into the given settings object."""
        camera_index = self.camera_combo.currentData()
        if camera_index is not None:  # scan may still be running
            settings.camera_index = camera_index
        settings.framerate = self.fps_spin.value()
        settings.exposure_auto = self.exposure_auto_check.isChecked()
        settings.exposure = self.exposure_spin.value()
        settings.record_interval = self.record_spin.value()
        settings.hold_interval = self.hold_spin.value()
        settings.threshold = self.threshold_slider.value()
        settings.blend_mode = self.blend_combo.currentText()
        settings.mirror = self.mirror_check.isChecked()
        settings.save_enabled = self.save_check.isChecked()
        settings.save_folder = self.folder_edit.text().strip() or "paintings"
