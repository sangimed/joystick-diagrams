"""Live SVG preview widgets for the Export page."""

from PySide6.QtCore import QByteArray, QTimer, Qt, Signal
from PySide6.QtGui import QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsScene,
    QGraphicsView,
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


class SvgPreviewView(QGraphicsView):
    """Pan/zoom SVG view backed by the same SVG text used for file export."""

    zoom_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._renderer: QSvgRenderer | None = None
        self._item: QGraphicsSvgItem | None = None
        self._auto_fit = True

        self.setScene(QGraphicsScene(self))
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setMinimumSize(320, 260)

    @property
    def has_preview(self) -> bool:
        return self._item is not None

    def load_svg(self, svg_data: str) -> bool:
        """Load in-memory SVG text. Returns False when Qt rejects the document."""
        renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")), self)
        if not renderer.isValid():
            renderer.deleteLater()
            self.clear_preview()
            return False

        scene = self.scene()
        old_renderer = self._renderer
        scene.clear()
        if old_renderer is not None:
            old_renderer.deleteLater()

        self._renderer = renderer
        self._item = QGraphicsSvgItem()
        self._item.setSharedRenderer(renderer)
        scene.addItem(self._item)
        scene.setSceneRect(self._item.boundingRect())

        self._auto_fit = True
        QTimer.singleShot(0, self.fit_content)
        return True

    def clear_preview(self) -> None:
        self.scene().clear()
        if self._renderer is not None:
            self._renderer.deleteLater()
        self._renderer = None
        self._item = None
        self.resetTransform()
        self.zoom_changed.emit(100)

    def fit_content(self) -> None:
        if self._item is None:
            return
        self.resetTransform()
        self.fitInView(self._item.boundingRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._auto_fit = True
        self._emit_zoom()

    def zoom_in(self) -> None:
        self._zoom_by(1.2)

    def zoom_out(self) -> None:
        self._zoom_by(1 / 1.2)

    def _zoom_by(self, factor: float) -> None:
        if self._item is None:
            return
        current_scale = self.transform().m11()
        proposed_scale = current_scale * factor
        if proposed_scale < 0.03 or proposed_scale > 30:
            return
        self.scale(factor, factor)
        self._auto_fit = False
        self._emit_zoom()

    def _emit_zoom(self) -> None:
        self.zoom_changed.emit(max(1, round(self.transform().m11() * 100)))

    def wheelEvent(self, event) -> None:
        if self._item is None:
            super().wheelEvent(event)
            return
        self._zoom_by(1.15 if event.angleDelta().y() > 0 else 1 / 1.15)
        event.accept()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self._auto_fit and self._item is not None:
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
            f"{mode} · live preview · exact export pipeline{warning_text}"
        )

    def show_svg(self, svg_data: str) -> bool:
        if not self.svg_view.load_svg(svg_data):
            self.show_empty("The generated SVG could not be rendered by Qt.")
            return False
        self.preview_stack.setCurrentWidget(self.svg_view)
        self._set_zoom_controls_enabled(True)
        return True

    def show_empty(self, message: str) -> None:
        self.svg_view.clear_preview()
        self.empty_label.setText(message)
        self.preview_stack.setCurrentWidget(self.empty_label)
        self._set_zoom_controls_enabled(False)

    def _set_zoom_controls_enabled(self, enabled: bool) -> None:
        self.zoom_out_btn.setEnabled(enabled)
        self.zoom_in_btn.setEnabled(enabled)
        self.fit_btn.setEnabled(enabled)

    def _on_zoom_changed(self, percent: int) -> None:
        self.zoom_label.setText(f"{percent}%")
