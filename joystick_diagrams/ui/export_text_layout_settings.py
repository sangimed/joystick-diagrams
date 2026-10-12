"""Settings widget for export-time binding label layout."""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.db.db_settings import add_update_setting_value
from joystick_diagrams.export_text_layout import (
    TEXT_ELLIPSIS_SETTING_KEY,
    TEXT_FONT_SIZE_SETTING_KEY,
    TEXT_LAYOUT_ENABLED_SETTING_KEY,
    TEXT_MAX_CHARS_SETTING_KEY,
    TEXT_MAX_LINES_SETTING_KEY,
    TEXT_MIN_FONT_SIZE_SETTING_KEY,
    TEXT_SHRINK_ENABLED_SETTING_KEY,
    TEXT_WRAP_ENABLED_SETTING_KEY,
    get_text_layout_options,
)
from joystick_diagrams.ui.widgets.section_header import SectionHeader


class ExportTextLayoutSettings(QWidget):
    """Configure wrapping and font fitting for dynamic SVG binding labels."""

    def __init__(self, parent=None):
        super().__init__(parent)
        options = get_text_layout_options()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        layout.addWidget(SectionHeader("fa5s.font", "Export Text Layout"))

        help_text = QLabel(
            "Optionally fit long binding names into template label boxes. "
            "The export engine can wrap text, shrink the font, and truncate only "
            "when you explicitly enable ellipsis. These settings affect exported "
            "binding labels only; template titles and static text are unchanged."
        )
        help_text.setObjectName("device_help_label")
        help_text.setWordWrap(True)
        layout.addWidget(help_text)

        form = QFormLayout()
        form.setSpacing(10)
        form.setContentsMargins(0, 0, 0, 0)

        self.enabled_cb = QCheckBox("Auto-fit binding labels")
        self.enabled_cb.setChecked(options.enabled)
        self.enabled_cb.setToolTip(
            "Enable smart layout for BUTTON, AXIS, POV and modifier action labels "
            "inserted during export. Disabled preserves the legacy export exactly."
        )
        form.addRow("", self.enabled_cb)

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(0, 48)
        self.font_size_spin.setSpecialValueText("Use template")
        self.font_size_spin.setSuffix(" px")
        self.font_size_spin.setValue(options.font_size)
        self.font_size_spin.setToolTip(
            "Override the template font size for dynamic labels. Leave at 'Use template' "
            "to preserve each template's font size until shrinking is needed."
        )
        form.addRow(self._label("Base label font size"), self._row(self.font_size_spin))

        self.wrap_cb = QCheckBox("Wrap long labels")
        self.wrap_cb.setChecked(options.wrap)
        self.wrap_cb.setToolTip(
            "Split long labels across lines. Action separators (|) are preferred as "
            "line-break opportunities before normal word wrapping."
        )
        form.addRow("", self.wrap_cb)

        self.max_chars_spin = QSpinBox()
        self.max_chars_spin.setRange(4, 120)
        self.max_chars_spin.setValue(options.max_chars)
        self.max_chars_spin.setToolTip(
            "Approximate number of characters that fit on one line at the base font size. "
            "This is intentionally template-independent and also drives auto-shrink."
        )
        form.addRow(
            self._label("Characters per line"), self._row(self.max_chars_spin)
        )

        self.max_lines_spin = QSpinBox()
        self.max_lines_spin.setRange(1, 8)
        self.max_lines_spin.setValue(options.max_lines)
        self.max_lines_spin.setToolTip(
            "Target maximum line count. Auto-shrink tries smaller font sizes before "
            "allowing additional lines. Ellipsis makes this a hard limit."
        )
        form.addRow(self._label("Maximum lines"), self._row(self.max_lines_spin))

        self.shrink_cb = QCheckBox("Shrink font when wrapping is not enough")
        self.shrink_cb.setChecked(options.shrink)
        self.shrink_cb.setToolTip(
            "Reduce long labels one pixel at a time until they reach the requested "
            "line count or the minimum font size."
        )
        form.addRow("", self.shrink_cb)

        self.min_font_size_spin = QSpinBox()
        self.min_font_size_spin.setRange(5, 48)
        self.min_font_size_spin.setSuffix(" px")
        self.min_font_size_spin.setValue(options.min_font_size)
        self.min_font_size_spin.setToolTip(
            "Smallest font size auto-shrink is allowed to use."
        )
        form.addRow(
            self._label("Minimum font size"), self._row(self.min_font_size_spin)
        )

        self.ellipsis_cb = QCheckBox("Use ellipsis if text still does not fit")
        self.ellipsis_cb.setChecked(options.ellipsis)
        self.ellipsis_cb.setToolTip(
            "When enabled, text that still exceeds the maximum line count at the "
            "minimum font size is truncated with an ellipsis. Disabled keeps all text."
        )
        form.addRow("", self.ellipsis_cb)

        layout.addLayout(form)

        self.enabled_cb.stateChanged.connect(self._on_enabled_changed)
        self.font_size_spin.valueChanged.connect(
            lambda value: self._store_int(TEXT_FONT_SIZE_SETTING_KEY, value)
        )
        self.wrap_cb.stateChanged.connect(self._on_wrap_changed)
        self.max_chars_spin.valueChanged.connect(
            lambda value: self._store_int(TEXT_MAX_CHARS_SETTING_KEY, value)
        )
        self.max_lines_spin.valueChanged.connect(
            lambda value: self._store_int(TEXT_MAX_LINES_SETTING_KEY, value)
        )
        self.shrink_cb.stateChanged.connect(self._on_shrink_changed)
        self.min_font_size_spin.valueChanged.connect(
            lambda value: self._store_int(TEXT_MIN_FONT_SIZE_SETTING_KEY, value)
        )
        self.ellipsis_cb.stateChanged.connect(
            lambda state: self._store_bool(TEXT_ELLIPSIS_SETTING_KEY, state)
        )

        self._sync_enabled_state()

    @staticmethod
    def _label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("device_help_label")
        return label

    @staticmethod
    def _row(widget: QWidget) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(widget)
        row.addStretch(1)
        return container

    @staticmethod
    def _store_bool(key: str, state: int) -> None:
        add_update_setting_value(
            key,
            "true" if state == Qt.CheckState.Checked.value else "false",
        )

    @staticmethod
    def _store_int(key: str, value: int) -> None:
        add_update_setting_value(key, str(value))

    def _on_enabled_changed(self, state: int) -> None:
        self._store_bool(TEXT_LAYOUT_ENABLED_SETTING_KEY, state)
        self._sync_enabled_state()

    def _on_wrap_changed(self, state: int) -> None:
        self._store_bool(TEXT_WRAP_ENABLED_SETTING_KEY, state)
        self._sync_enabled_state()

    def _on_shrink_changed(self, state: int) -> None:
        self._store_bool(TEXT_SHRINK_ENABLED_SETTING_KEY, state)
        self._sync_enabled_state()

    def _sync_enabled_state(self) -> None:
        enabled = self.enabled_cb.isChecked()
        wrap = enabled and self.wrap_cb.isChecked()
        shrink = enabled and self.shrink_cb.isChecked()

        self.font_size_spin.setEnabled(enabled)
        self.wrap_cb.setEnabled(enabled)
        self.max_chars_spin.setEnabled(enabled)
        self.max_lines_spin.setEnabled(wrap)
        self.shrink_cb.setEnabled(enabled)
        self.min_font_size_spin.setEnabled(shrink)
        self.ellipsis_cb.setEnabled(enabled and self.wrap_cb.isChecked())
