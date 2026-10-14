from joystick_diagrams.ui.export_page import ExportPage


def test_export_page_declares_live_preview_integration():
    # Keep this test purely structural. Instantiating nested QMainWindow widgets in
    # pytest-qt on Windows can trigger native Qt access violations that are unrelated
    # to the preview feature itself. The actual preview widget behavior is covered in
    # test_export_preview.py.
    assert ExportPage.PREVIEW_DEBOUNCE_MS == 180
    assert hasattr(ExportPage, "_refresh_preview")
    assert hasattr(ExportPage, "_schedule_preview_refresh")
    assert hasattr(ExportPage, "_restore_preview_selection")


def test_export_page_prioritises_preview_width():
    assert ExportPage.PREVIEW_DEVICE_PANE_PX == 340
    assert ExportPage.PREVIEW_SPLITTER_SIZES == (340, 1200)
