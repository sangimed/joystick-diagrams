from types import SimpleNamespace
from unittest.mock import patch

from joystick_diagrams.ui.export_page import ExportPage
from joystick_diagrams.ui.export_preview import ExportPreviewPanel


def test_export_page_contains_live_preview_workspace(qtbot):
    # Keep this structural test independent from global AppState/plugin setup and
    # avoid profile discovery / WebEngine startup in headless CI.
    app_state = SimpleNamespace(output_plugin_manager=None)

    with (
        patch("joystick_diagrams.ui.export_page.AppState", return_value=app_state),
        patch("joystick_diagrams.ui.device_setup.DeviceSetup.initialise_ui"),
    ):
        page = ExportPage()

    qtbot.addWidget(page)

    assert page.preview_splitter.count() == 2
    assert page.preview_splitter.widget(0) is page.device_widget
    assert page.preview_splitter.widget(1) is page.preview_panel
    assert isinstance(page.preview_panel, ExportPreviewPanel)
    assert page._preview_timer.isSingleShot() is True
