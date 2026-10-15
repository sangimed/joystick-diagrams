import pytest

from joystick_diagrams.ui.export_preview import (
    ExportPreviewPanel,
    SvgPreviewView,
    parse_svg_dimensions,
)


def test_parse_svg_dimensions_prefers_viewbox_over_physical_size():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="396.35mm" height="206.38mm" '
        'viewBox="0 0 1498 780"></svg>'
    )

    assert parse_svg_dimensions(svg) == (1498.0, 780.0)


def test_parse_svg_dimensions_converts_physical_units_without_viewbox():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="25.4mm" height="2.54cm">'
        "</svg>"
    )

    width, height = parse_svg_dimensions(svg)
    assert width == pytest.approx(96.0)
    assert height == pytest.approx(96.0)


def test_parse_svg_dimensions_uses_explicit_pixel_size_without_viewbox():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="1498" height="780"></svg>'

    assert parse_svg_dimensions(svg) == (1498.0, 780.0)


def test_parse_svg_dimensions_falls_back_to_default():
    svg = '<svg xmlns="http://www.w3.org/2000/svg"></svg>'

    assert parse_svg_dimensions(svg) == (800.0, 600.0)


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


def test_preview_panel_prefers_compact_device_pane():
    assert ExportPreviewPanel.PREFERRED_DEVICE_PANE_PX == 340


def test_preview_panel_is_preview_only(qtbot):
    panel = ExportPreviewPanel()
    qtbot.addWidget(panel)

    assert not hasattr(panel, "layout_settings")
    assert not hasattr(panel, "controls_frame")
    assert not hasattr(panel, "text_layout_btn")
    assert panel.preview_stack.minimumWidth() >= 0
