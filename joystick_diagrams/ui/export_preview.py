"""Live Chromium-backed SVG preview widgets for the Export page."""

from pathlib import Path
import re

from PySide6.QtCore import QTemporaryDir, QTimer, Qt, QUrl, Signal
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from joystick_diagrams.export_text_layout import get_text_layout_options
from joystick_diagrams.ui.export_text_layout_settings import ExportTextLayoutSettings


_DIMENSION_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)")
_VIEWBOX_RE = re.compile(
    r"\bviewBox\s*=\s*(['\"])\s*[-+0-9.eE]+\s+[-+0-9.eE]+\s+"
    r"([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*\1",
    flags=re.IGNORECASE,
)


def _parse_dimension(value: str | None) -> float | None:
    if not value:
        return None
    match = _DIMENSION_RE.match(value)
    if not match:
        return None
    try:
        return float(match.group(1))
    except ValueError:
        return None


def parse_svg_dimensions(svg_data: str) -> tuple[float, float]:
    """Best-effort SVG dimensions for Fit; rendering remains Chromium-owned."""
    root_match = re.search(r"<svg\b(?P<attrs>[^>]*)>", svg_data, re.IGNORECASE)
    if not root_match:
        return (800.0, 600.0)

    attrs = root_match.group("attrs")

    def attribute(name: str) -> str | None:
        match = re.search(
            rf"\b{re.escape(name)}\s*=\s*(['\"])(.*?)\1",
            attrs,
            flags=re.IGNORECASE | re.DOTALL,
        )
        return match.group(2) if match else None

    width = _parse_dimension(attribute("width"))
    height = _parse_dimension(attribute("height"))
    if width and height:
        return (width, height)

    viewbox = _VIEWBOX_RE.search(root_match.group(0))
    if viewbox:
        try:
            viewbox_width = float(viewbox.group(2))
            viewbox_height = float(viewbox.group(3))
            if viewbox_width > 0 and viewbox_height > 0:
                return (viewbox_width, viewbox_height)
        except ValueError:
            pass

    return (800.0, 600.0)


class _PreviewWebView(QWebEngineView):
    """QWebEngineView with drag-to-pan and wheel-to-zoom controls."""

    zoom_requested = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._panning = False
        self._last_pos = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def wheelEvent(self, event) -> None:
        self.zoom_requested.emit(1.15 if event.angleDelta().y() > 0 else 1 / 1.15)
        event.accept()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._panning = True
            self._last_pos = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning and self._last_pos is not None:
            delta = event.position() - self._last_pos
            self._last_pos = event.position()
            self.page().runJavaScript(
                f"window.scrollBy({-delta.x():.2f}, {-delta.y():.2f});"
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._panning:
            self._panning = False
            self._last_pos = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)


class SvgPreviewView(QWidget):
    """Pan/zoom SVG view using Chromium for draw.io ``foreignObject`` support."""

    zoom_changed = Signal(int)
    load_failed = Signal()

    MIN_ZOOM = 0.25
    MAX_ZOOM = 5.0

    def __init__(self, parent=None):
        super().__init__(parent)
        self._web_view: _PreviewWebView | None = None
        self._svg_size = (800.0, 600.0)
        self._has_preview = False
        self._auto_fit = True
        self._zoom_factor = 1.0
        self._temp_dir = QTemporaryDir()
        self._preview_path = (
            Path(self._temp_dir.path()) / "preview.svg"
            if self._temp_dir.isValid()
            else None
        )

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setMinimumSize(320, 260)

    @property
    def has_preview(self) -> bool:
        return self._has_preview

    def _ensure_web_view(self) -> _PreviewWebView:
        if self._web_view is not None:
            return self._web_view

        view = _PreviewWebView(self)
        view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        view.zoom_requested.connect(self._zoom_by)
        view.loadFinished.connect(self._on_load_finished)
        self._layout.addWidget(view)
        self._web_view = view
        return view

    def load_svg(self, svg_data: str) -> bool:
        """Render generated SVG through a private temporary file in Chromium.

        QWebEngine's ``setContent`` uses a data URL internally and is subject to a
        small URL-size limit. draw.io templates can be several megabytes, so the
        preview writes only to a QTemporaryDir and loads that file locally. The
        bytes are still exactly those returned by ``populate_template()``.
        """
        if re.search(r"<svg\b", svg_data, re.IGNORECASE) is None:
            self.clear_preview()
            return False
        if self._preview_path is None:
            self.clear_preview()
            return False

        try:
            self._preview_path.write_text(svg_data, encoding="utf-8")
        except OSError:
            self.clear_preview()
            return False

        self._svg_size = parse_svg_dimensions(svg_data)
        self._has_preview = True
        self._auto_fit = True

        view = self._ensure_web_view()
        view.show()
        view.load(QUrl.fromLocalFile(str(self._preview_path.resolve())))
        return True

    def clear_preview(self) -> None:
        self._has_preview = False
        self._auto_fit = True
        self._zoom_factor = 1.0
        if self._web_view is not None:
            self._web_view.hide()
        self.zoom_changed.emit(100)

    def fit_content(self) -> None:
        if not self._has_preview or self._web_view is None:
            return

        width, height = self._svg_size
        viewport = self._web_view.viewport().size()
        if width <= 0 or height <= 0 or viewport.width() <= 0 or viewport.height() <= 0:
            return

        factor = min(viewport.width() / width, viewport.height() / height) * 0.94
        self._set_zoom_factor(factor, auto_fit=True)
        self._web_view.page().runJavaScript("window.scrollTo(0, 0);")

    def zoom_in(self) -> None:
        self._zoom_by(1.2)

    def zoom_out(self) -> None:
        self._zoom_by(1 / 1.2)

    def _zoom_by(self, factor: float) -> None:
        if not self._has_preview:
            return
        self._set_zoom_factor(self._zoom_factor * factor, auto_fit=False)

    def _set_zoom_factor(self, factor: float, *, auto_fit: bool) -> None:
        if self._web_view is None:
            return
        clamped = min(self.MAX_ZOOM, max(self.MIN_ZOOM, factor))
        self._zoom_factor = clamped
        self._auto_fit = auto_fit
        self._web_view.setZoomFactor(clamped)
        self.zoom_changed.emit(round(clamped * 100))

    def _on_load_finished(self, ok: bool) -> None:
        if not self._has_preview:
            return
        if not ok:
            self._has_preview = False
            self.load_failed.emit()
            return
        if self._auto_fit:
            QTimer.singleShot(0, self.fit_content)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._auto_fit and self._has_preview:
            QTimer.singleShot(0, self.fit_content)


class ExportPreviewPanel(QWidget):
    """Text-layout controls and live SVG preview used by the Export page."""

    settings_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        header = QVBoxLayout()
        header.setSpacing(2)
        self.title_label = QLabel("Live preview")
        self.title_label.setStyleSheet("font-weight: 600;")
        header.addWidget(self.title_label)

        self.context_label = QLabel("Select a profile to preview its generated diagram")
        self.context_label.setObjectName("device_help_label")
        self.context_label.setWordWrap(True)
        header.addWidget(self.context_label)
        root.addLayout(header)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(10)

        controls_frame = QFrame()
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(8, 8, 8, 8)
        controls_layout.setSpacing(0)

        self.layout_settings = ExportTextLayoutSettings(controls_frame, compact=True)
        self.layout_settings.settings_changed.connect(self.settings_changed.emit)

        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setFrameShape(QFrame.Shape.NoFrame)
        controls_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        controls_scroll.setWidget(self.layout_settings)
        controls_scroll.setMinimumWidth(270)
        controls_scroll.setMaximumWidth(330)
        controls_layout.addWidget(controls_scroll)
        body.addWidget(controls_frame, 0)

        preview_frame = QFrame()
        preview_layout = QVBoxLayout(preview_frame)
        preview_layout.setContentsMargins(0, 0, 0, 0)
        preview_layout.setSpacing(6)

        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(0, 0, 0, 0)
        toolbar.addStretch(1)

        self.zoom_out_btn = QPushButton("−")
        self.zoom_out_btn.setFixedWidth(34)
        self.zoom_out_btn.setToolTip("Zoom out")
        toolbar.addWidget(self.zoom_out_btn)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setMinimumWidth(48)
        self.zoom_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar.addWidget(self.zoom_label)

        self.zoom_in_btn = QPushButton("+")
        self.zoom_in_btn.setFixedWidth(34)
        self.zoom_in_btn.setToolTip("Zoom in")
        toolbar.addWidget(self.zoom_in_btn)

        self.fit_btn = QPushButton("Fit")
        self.fit_btn.setToolTip("Fit the full diagram in the preview")
        toolbar.addWidget(self.fit_btn)
        preview_layout.addLayout(toolbar)

        self.preview_stack = QStackedWidget()
        self.empty_label = QLabel("Select a profile with a template to preview it here.")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setWordWrap(True)
        self.empty_label.setObjectName("device_help_label")
        self.preview_stack.addWidget(self.empty_label)

        self.svg_view = SvgPreviewView()
        self.svg_view.load_failed.connect(self._on_preview_load_failed)
        self.preview_stack.addWidget(self.svg_view)
        preview_layout.addWidget(self.preview_stack, 1)

        self.status_label = QLabel("Preview uses the exact SVG export pipeline.")
        self.status_label.setObjectName("device_help_label")
        self.status_label.setWordWrap(True)
        preview_layout.addWidget(self.status_label)

        body.addWidget(preview_frame, 1)
        root.addLayout(body, 1)

        self.zoom_out_btn.clicked.connect(self.svg_view.zoom_out)
        self.zoom_in_btn.clicked.connect(self.svg_view.zoom_in)
        self.fit_btn.clicked.connect(self.svg_view.fit_content)
        self.svg_view.zoom_changed.connect(self._on_zoom_changed)

        self.show_empty("Select a profile to preview its generated diagram.")

    def reload_settings(self) -> None:
        self.layout_settings.reload_from_settings()

    def set_context(
        self,
        device_name: str,
        profile_name: str,
        template_name: str | None,
        warning_count: int = 0,
    ) -> None:
        template_text = template_name or "No template"
        self.context_label.setText(
            f"{device_name} · {profile_name} · {template_text}"
        )
        options = get_text_layout_options()
        mode = "Auto-fit ON" if options.enabled else "Auto-fit OFF"
        warning_text = (
            f" · {warning_count} template warning{'s' if warning_count != 1 else ''}"
            if warning_count
            else ""
        )
        self.status_label.setText(
            f"{mode} · live Chromium preview · exact export pipeline{warning_text}"
        )

    def show_svg(self, svg_data: str) -> bool:
        if not self.svg_view.load_svg(svg_data):
            self.show_empty("The generated SVG could not be loaded for preview.")
            return False
        self.preview_stack.setCurrentWidget(self.svg_view)
        self._set_zoom_controls_enabled(True)
        return True

    def show_empty(self, message: str) -> None:
        self.svg_view.clear_preview()
        self.empty_label.setText(message)
        self.preview_stack.setCurrentWidget(self.empty_label)
        self._set_zoom_controls_enabled(False)

    def _on_preview_load_failed(self) -> None:
        self.show_empty("Chromium could not render the generated SVG preview.")

    def _set_zoom_controls_enabled(self, enabled: bool) -> None:
        self.zoom_out_btn.setEnabled(enabled)
        self.zoom_in_btn.setEnabled(enabled)
        self.fit_btn.setEnabled(enabled)

    def _on_zoom_changed(self, percent: int) -> None:
        self.zoom_label.setText(f"{percent}%")
