from joystick_diagrams.ui.export_preview import (
    ExportPreviewPanel,
    SvgPreviewView,
    parse_svg_dimensions,
)


def test_parse_svg_dimensions_prefers_explicit_size():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1498" height="780"></svg>'

    assert parse_svg_dimensions(svg) == (1498.0, 780.0)


def test_parse_svg_dimensions_falls_back_to_viewbox():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 700"></svg>'

    assert parse_svg_dimensions(svg) == (1200.0, 700.0)


def test_svg_preview_creates_webengine_lazily(qtbot):
    view = SvgPreviewView()
    qtbot.addWidget(view)

    assert view.has_preview is False
    assert view._web_view is None
    assert view.load_svg("not svg") is False
    assert view._web_view is None


def test_preview_panel_context_reports_warnings(qtbot):
    panel = ExportPreviewPanel()
    qtbot.addWidget(panel)

    panel.set_context("X52 Pro", "Default", "x52.svg", warning_count=2)

    assert "X52 Pro" in panel.context_label.text()
    assert "2 template warnings" in panel.status_label.text()
    assert panel.svg_view._web_view is None


def test_preview_panel_forwards_text_layout_changes(qtbot):
    panel = ExportPreviewPanel()
    qtbot.addWidget(panel)
    changes = []
    panel.settings_changed.connect(lambda: changes.append(True))

    panel.layout_settings.enabled_cb.setChecked(True)

    assert changes
