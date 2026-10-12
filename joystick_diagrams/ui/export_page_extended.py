"""Export page extension with an in-memory live SVG preview."""

import logging

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QSplitter, QTreeWidgetItem

from joystick_diagrams.export import populate_template
from joystick_diagrams.export_device import ExportDevice
from joystick_diagrams.ui.export_page import ExportPage as BaseExportPage
from joystick_diagrams.ui.export_preview import ExportPreviewPanel

_logger = logging.getLogger(__name__)


class ExportPage(BaseExportPage):
    """Core Export page with live text-layout tuning and exact SVG preview."""

    PREVIEW_DEBOUNCE_MS = 180

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._preview_export_device: ExportDevice | None = None
        self._preview_identity: tuple[str, str] | None = None

        self._preview_timer = QTimer(self)
        self._preview_timer.setSingleShot(True)
        self._preview_timer.setInterval(self.PREVIEW_DEBOUNCE_MS)
        self._preview_timer.timeout.connect(self._refresh_preview)

        self.preview_panel = ExportPreviewPanel(self)
        self.preview_panel.settings_changed.connect(self._schedule_preview_refresh)

        # Replace the original single device tree with a resizable tree/preview split.
        self.devices_container.removeWidget(self.device_widget)
        self.preview_splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.preview_splitter.setChildrenCollapsible(False)
        self.preview_splitter.addWidget(self.device_widget)
        self.preview_splitter.addWidget(self.preview_panel)
        self.preview_splitter.setStretchFactor(0, 3)
        self.preview_splitter.setStretchFactor(1, 5)
        self.preview_splitter.setSizes([420, 700])
        self.devices_container.addWidget(self.preview_splitter)

        self.device_widget.device_item_selected.connect(self._on_preview_item_selected)
        self.device_widget.devices_updated.connect(self._on_devices_updated)

        QTimer.singleShot(0, self._select_initial_preview)

    def refresh(self):
        """Refresh output plugins, persisted layout settings, and the preview."""
        super().refresh()
        self.preview_panel.reload_settings()
        QTimer.singleShot(0, self._restore_preview_selection)

    def _export_device_from_item(
        self, item: QTreeWidgetItem | None
    ) -> ExportDevice | None:
        if item is None:
            return None

        if item.parent() is not None:
            data = item.data(0, Qt.ItemDataRole.UserRole)
            return data if isinstance(data, ExportDevice) else None

        # Device root selected: preview the first checked profile, otherwise the first.
        fallback = None
        for index in range(item.childCount()):
            child = item.child(index)
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if not isinstance(data, ExportDevice):
                continue
            if fallback is None:
                fallback = data
            if child.checkState(0) == Qt.CheckState.Checked:
                return data
        return fallback

    def _on_preview_item_selected(self, item: QTreeWidgetItem) -> None:
        export_device = self._export_device_from_item(item)
        if export_device is None:
            self._preview_export_device = None
            self._preview_identity = None
            self.preview_panel.show_empty(
                "Select a profile with a template to preview it here."
            )
            return

        self._preview_export_device = export_device
        self._preview_identity = (
            export_device.device_id,
            export_device.profile_wrapper.profile_name,
        )
        self._schedule_preview_refresh()

    def _schedule_preview_refresh(self) -> None:
        self._preview_timer.start()

    def _refresh_preview(self) -> None:
        export_device = self._preview_export_device
        if export_device is None:
            self.preview_panel.show_empty(
                "Select a profile with a template to preview it here."
            )
            return

        self.preview_panel.set_context(
            export_device.device_name,
            export_device.profile_wrapper.profile_name,
            export_device.template_file_name,
            len(export_device.errors),
        )

        if not export_device.has_template:
            self.preview_panel.show_empty(
                "Assign an SVG template to this device to enable live preview."
            )
            return

        try:
            # Deliberately use populate_template(): this is the exact same in-memory
            # SVG generation step used immediately before a real file export.
            svg_data = populate_template(export_device)
        except Exception as exc:
            _logger.exception("Unable to generate live export preview")
            self.preview_panel.show_empty(f"Preview generation failed: {exc}")
            return

        self.preview_panel.show_svg(svg_data)

    def _select_initial_preview(self) -> None:
        current = self.device_widget.treeWidget.currentItem()
        if current is not None and self._export_device_from_item(current) is not None:
            self._on_preview_item_selected(current)
            return

        tree = self.device_widget.treeWidget
        for root_index in range(tree.topLevelItemCount()):
            root = tree.topLevelItem(root_index)
            if root.childCount() == 0:
                continue
            child = root.child(0)
            tree.setCurrentItem(child)
            self._on_preview_item_selected(child)
            return

        self.preview_panel.show_empty(
            "No exportable profile with an assigned template is available."
        )

    def _on_devices_updated(self) -> None:
        # DeviceSetup rebuilds the QTreeWidget synchronously before this slot runs.
        # Defer selection one event-loop turn so Qt has finished updating widgets.
        QTimer.singleShot(0, self._restore_preview_selection)

    def _restore_preview_selection(self) -> None:
        identity = self._preview_identity
        if identity is None:
            self._select_initial_preview()
            return

        device_id, profile_name = identity
        tree = self.device_widget.treeWidget
        for root_index in range(tree.topLevelItemCount()):
            root = tree.topLevelItem(root_index)
            for child_index in range(root.childCount()):
                child = root.child(child_index)
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if not isinstance(data, ExportDevice):
                    continue
                if (
                    data.device_id == device_id
                    and data.profile_wrapper.profile_name == profile_name
                ):
                    tree.setCurrentItem(child)
                    self._on_preview_item_selected(child)
                    return

        self._preview_identity = None
        self._select_initial_preview()
