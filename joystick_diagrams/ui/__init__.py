"""UI package exports."""

# MainWindow imports these modules from this package. Point the public names at
# small extensions so the large existing pages remain untouched and the feature
# stays easy to review/rebase.
from joystick_diagrams.ui import export_page_extended as export_page
from joystick_diagrams.ui import settings_page_extended as settings_page

__all__ = ["export_page", "settings_page"]
