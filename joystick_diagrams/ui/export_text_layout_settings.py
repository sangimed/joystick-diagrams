"""Settings widget for export-time binding label layout."""

from functools import partial

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.db.db_settings import add_update_setting_value
from joystick_diagrams.export_text_layout import (
    DEFAULT_TEXT_ELLIPSIS_ENABLED,
    DEFAULT_TEXT_FONT_SIZE,
    DEFAULT_TEXT_LAYOUT_ENABLED,
    DEFAULT_TEXT_MAX_CHARS,
    DEFAULT_TEXT_MAX_LINES,
    DEFAULT_TEXT_MIN_FONT_SIZE,
    DEFAULT_TEXT_SHRINK_ENABLED,
    DEFAULT_TEXT_WRAP_ENABLED,
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

    settings_changed = Signal()

    def __init__(self, parent=None, *, compact: bool = False):
        super().__init__(parent)
        self.compact = compact

        self.enabled_cb = QCheckBox("Auto-fit" if compact else "Auto-fit binding labels")
        self.enabled_cb.setToolTip(
            "Enable smart layout for BUTTON, AXIS, POV and modifier action labels "
            "inserted during export. Disabled preserves the legacy export exactly."
        )

        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(0, 48)
        self.font_size_spin.setSpecialValueText("Use template")
        self.font_size_spin.setSuffix(" px")
        self.font_size_spin.setToolTip(
            "Override the template font size for dynamic labels. Leave at 'Use template' "
            "to preserve each template's font size until shrinking is needed."
        )

        self.wrap_cb = QCheckBox("Wrap" if compact else "Wrap long labels")
        self.wrap_cb.setToolTip(
            "Split long labels across lines. Action separators (|) are preferred as "
            "line-break opportunities before normal word wrapping."
        )

        self.max_chars_spin = QSpinBox()
        self.max_chars_spin.setRange(4, 120)
        self.max_chars_spin.setToolTip(
            "Approximate number of characters that fit on one line at the base font size. "
            "This is template-independent and also drives auto-shrink."
        )

        self.max_lines_spin = QSpinBox()
        self.max_lines_spin.setRange(1, 8)
        self.max_lines_spin.setToolTip(
            "Target maximum line count. Auto-shrink tries smaller font sizes before "
            "allowing additional lines. Ellipsis makes this a hard limit."
        )

        self.shrink_cb = QCheckBox(
            "Shrink" if compact else "Shrink font when wrapping is not enough"
        )
        self.shrink_cb.setToolTip(
            "Reduce long labels one pixel at a time until they reach the requested "
            "line count or the minimum font size."
        )

        self.min_font_size_spin = QSpinBox()
        self.min_font_size_spin.setRange(5, 48)
        self.min_font_size_spin.setSuffix(" px")
        self.min_font_size_spin.setToolTip(
            "Smallest font size auto-shrink is allowed to use."
        )

        self.ellipsis_cb = QCheckBox(
            "Ellipsis" if compact else "Use ellipsis if text still does not fit"
        )
        self.ellipsis_cb.setToolTip(
            "When enabled, text that still exceeds the maximum line count at the "
            "minimum font size is truncated with an ellipsis. Disabled keeps all text."
        )

        self.reset_defaults_btn = QPushButton("Reset" if compact else "Reset defaults")
        self.reset_defaults_btn.setToolTip(
            "Restore the built-in export text layout defaults."
        )

        self.use_template_font_btn = QPushButton(
            "Template font" if compact else "Use template font"
        )
        self.use_template_font_btn.setToolTip(
            "Stop overriding the template font size while keeping the other text layout settings."
        )

        if compact:
            self._build_compact_ui()
        else:
            self._build_full_ui()

        self.enabled_cb.stateChanged.connect(self._on_enabled_changed)
        self.font_size_spin.valueChanged.connect(
            partial(self._store_int, TEXT_FONT_SIZE_SETTING_KEY)
        )
        self.wrap_cb.stateChanged.connect(self._on_wrap_changed)
        self.max_chars_spin.valueChanged.connect(
            partial(self._store_int, TEXT_MAX_CHARS_SETTING_KEY)
        )
        self.max_lines_spin.valueChanged.connect(
            partial(self._store_int, TEXT_MAX_LINES_SETTING_KEY)
        )
        self.shrink_cb.stateChanged.connect(self._on_shrink_changed)
        self.min_font_size_spin.valueChanged.connect(
            partial(self._store_int, TEXT_MIN_FONT_SIZE_SETTING_KEY)
        )
        self.ellipsis_cb.stateChanged.connect(
            partial(self._store_bool, TEXT_ELLIPSIS_SETTING_KEY)
        )
        self.reset_defaults_btn.clicked.connect(self.reset_defaults)
        self.use_template_font_btn.clicked.connect(self.use_template_font)

        self.reload_from_settings()

    def _build_compact_ui(self) -> None:
        """Build the two-row horizontal controls used by the Export header."""
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )
        self.setMaximumHeight(104)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        title = QLabel("Text layout")
        title.setStyleSheet("font-weight: 600;")
        layout.addWidget(title)

        self.font_size_spin.setMaximumWidth(112)
        self.max_chars_spin.setMaximumWidth(64)
        self.max_lines_spin.setMaximumWidth(58)
        self.min_font_size_spin.setMaximumWidth(72)

        self.quick_grid = QGridLayout()
        self.quick_grid.setContentsMargins(0, 0, 0, 0)
        self.quick_grid.setHorizontalSpacing(10)
        self.quick_grid.setVerticalSpacing(4)

        self.quick_grid.addWidget(self.enabled_cb, 0, 0)
        self.quick_grid.addWidget(
            self._compact_field("Font", self.font_size_spin), 0, 1
        )
        self.quick_grid.addWidget(self.wrap_cb, 0, 2)
        self.quick_grid.addWidget(
            self._compact_field("Chars", self.max_chars_spin), 0, 3
        )
        self.quick_grid.addWidget(
            self._compact_field("Lines", self.max_lines_spin), 0, 4
        )

        self.quick_grid.addWidget(self.shrink_cb, 1, 0)
        self.quick_grid.addWidget(
            self._compact_field("Min font", self.min_font_size_spin), 1, 1
        )
        self.quick_grid.addWidget(self.ellipsis_cb, 1, 2)

        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(6)
        actions_layout.addWidget(self.reset_defaults_btn)
        actions_layout.addWidget(self.use_template_font_btn)
        self.quick_grid.addWidget(actions, 1, 3, 1, 2)

        self.quick_grid.setColumnStretch(4, 1)
        layout.addLayout(self.quick_grid)

    def _build_full_ui(self) -> None:
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
        form.addRow("", self.enabled_cb)
        form.addRow(self._label("Base label font size"), self._row(self.font_size_spin))
        form.addRow("", self.wrap_cb)
        form.addRow(
            self._label("Characters per line"), self._row(self.max_chars_spin)
        )
        form.addRow(self._label("Maximum lines"), self._row(self.max_lines_spin))
        form.addRow("", self.shrink_cb)
        form.addRow(
            self._label("Minimum font size"), self._row(self.min_font_size_spin)
        )
        form.addRow("", self.ellipsis_cb)
        layout.addLayout(form)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 2, 0, 0)
        actions.setSpacing(6)
        actions.addWidget(self.reset_defaults_btn)
        actions.addWidget(self.use_template_font_btn)
        actions.addStretch(1)
        layout.addLayout(actions)

    @staticmethod
    def _compact_field(text: str, widget: QWidget) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        label = QLabel(text)
        label.setObjectName("device_help_label")
        row.addWidget(label)
        row.addWidget(widget)
        return container

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
    def _bool_to_storage(state: int) -> str:
        return "true" if state == Qt.CheckState.Checked.value else "false"

    def _store_bool(self, key: str, state: int) -> None:
        add_update_setting_value(key, self._bool_to_storage(state))
        self.settings_changed.emit()

    def _store_int(self, key: str, value: int) -> None:
        add_update_setting_value(key, str(value))
        self.settings_changed.emit()

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
        self.use_template_font_btn.setEnabled(enabled)

    def reload_from_settings(self) -> None:
        """Refresh controls from persisted settings without writing them back."""
        options = get_text_layout_options()
        widgets = (
            self.enabled_cb,
            self.font_size_spin,
            self.wrap_cb,
            self.max_chars_spin,
            self.max_lines_spin,
            self.shrink_cb,
            self.min_font_size_spin,
            self.ellipsis_cb,
        )
        blockers = [QSignalBlocker(widget) for widget in widgets]
        try:
            self.enabled_cb.setChecked(options.enabled)
            self.font_size_spin.setValue(options.font_size)
            self.wrap_cb.setChecked(options.wrap)
            self.max_chars_spin.setValue(options.max_chars)
            self.max_lines_spin.setValue(options.max_lines)
            self.shrink_cb.setChecked(options.shrink)
            self.min_font_size_spin.setValue(options.min_font_size)
            self.ellipsis_cb.setChecked(options.ellipsis)
        finally:
            del blockers
        self._sync_enabled_state()

    def reset_defaults(self) -> None:
        """Restore built-in defaults and notify live preview consumers once."""
        values = {
            TEXT_LAYOUT_ENABLED_SETTING_KEY: "true"
            if DEFAULT_TEXT_LAYOUT_ENABLED
            else "false",
            TEXT_WRAP_ENABLED_SETTING_KEY: "true"
            if DEFAULT_TEXT_WRAP_ENABLED
            else "false",
            TEXT_MAX_CHARS_SETTING_KEY: str(DEFAULT_TEXT_MAX_CHARS),
            TEXT_MAX_LINES_SETTING_KEY: str(DEFAULT_TEXT_MAX_LINES),
            TEXT_FONT_SIZE_SETTING_KEY: str(DEFAULT_TEXT_FONT_SIZE),
            TEXT_SHRINK_ENABLED_SETTING_KEY: "true"
            if DEFAULT_TEXT_SHRINK_ENABLED
            else "false",
            TEXT_MIN_FONT_SIZE_SETTING_KEY: str(DEFAULT_TEXT_MIN_FONT_SIZE),
            TEXT_ELLIPSIS_SETTING_KEY: "true"
            if DEFAULT_TEXT_ELLIPSIS_ENABLED
            else "false",
        }
        for key, value in values.items():
            add_update_setting_value(key, value)
        self.reload_from_settings()
        self.settings_changed.emit()

    def use_template_font(self) -> None:
        """Clear the global font-size override while preserving other options."""
        if self.font_size_spin.value() == 0:
            self.settings_changed.emit()
            return
        self.font_size_spin.setValue(0)
