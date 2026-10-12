from joystick_diagrams.ui.export_preview import ExportPreviewPanel, SvgPreviewView


VALID_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" '
    'viewBox="0 0 200 100">'
    '<rect x="0" y="0" width="200" height="100"/>'
    "</svg>"
)


def test_svg_preview_loads_in_memory_svg(qtbot):
    view = SvgPreviewView()
    qtbot.addWidget(view)

    assert view.load_svg(VALID_SVG) is True
    assert view.has_preview is True
    assert len(view.scene().items()) == 1


def test_svg_preview_rejects_invalid_svg(qtbot):
    view = SvgPreviewView()
    qtbot.addWidget(view)

    assert view.load_svg("not svg") is False
    assert view.has_preview is False


def test_preview_panel_switches_to_live_preview(qtbot):
    panel = ExportPreviewPanel()
    qtbot.addWidget(panel)

    panel.set_context("X52 Pro", "Default", "x52.svg", warning_count=2)
    assert panel.show_svg(VALID_SVG) is True

    assert panel.preview_stack.currentWidget() is panel.svg_view
    assert panel.zoom_in_btn.isEnabled() is True
    assert "X52 Pro" in panel.context_label.text()
    assert "2 template warnings" in panel.status_label.text()


def test_preview_panel_forwards_text_layout_changes(qtbot):
    panel = ExportPreviewPanel()
    qtbot.addWidget(panel)
    changes = []
    panel.settings_changed.connect(lambda: changes.append(True))

    panel.layout_settings.enabled_cb.setChecked(True)

    assert changes
