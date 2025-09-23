"""
Main application window for Household Tracker.

Currently uses placeholder tabs for:
- Chores
- Purchases
- History
- Analytics

Each tab is populated with a simple QLabel until the corresponding feature
is implemented. This scaffolding allows the UI structure to be tested
before full functionality is built.
"""


from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from src.views.users_dialog import UsersDialog


class MainWindow(QMainWindow):
    """The main top-level window of the Household Tracker application."""

    def __init__(self):
        """
        Initialize the main window with a tabbed layout.

        - Sets the title and default size.
        - Adds four placeholder tabs (Chores, Purchases, History, Analytics).
        - Wraps the QTabWidget in a central QWidget with a vertical layout.
        """
        super().__init__()
        self.setWindowTitle("Household Tracker")
        self.resize(1100, 720)

        # Menu: Settings -> Users...
        menubar = self.menuBar()
        settings_menu = menubar.addMenu("&Settings")

        act_users = QAction("Users...", self)
        act_users.triggered.connect(self.open_users_dialog)
        settings_menu.addAction(act_users)

        # View -> Appearance -> Light, Dark
        view_menu = menubar.addMenu("&View")
        appearance_menu = view_menu.addMenu("Appearance")

        self.act_light = QAction("Light Mode", self, checkable=True)
        self.act_dark = QAction("Dark Mode", self, checkable=True)

        # Exclusive selection (radio behaviour)
        group = QActionGroup(self)
        group.setExclusive(True)
        group.addAction(self.act_light)
        group.addAction(self.act_dark)

        appearance_menu.addAction(self.act_light)
        appearance_menu.addAction(self.act_dark)

        # Load savaed mode and apply checkmarks + stylesheet
        mode = self._current_theme_mode()   # light or dark
        self._apply_theme(mode)
        self.act_light.setChecked(mode == "light")
        self.act_dark.setChecked(mode == "dark")

        # Switch theme when toggled ON (avoid double triggers)
        self.act_light.toggled.connect(lambda checked: checked and self._apply_theme("light"))
        self.act_dark.toggled.connect(lambda checked: checked and self._apply_theme("dark"))

        # Create a QTabWidget to hold feature areas
        tabs = QTabWidget()
        tabs.addTab(self._make_placeholder("Chores board coming soon…"), "Chores")
        tabs.addTab(self._make_placeholder("Purchases board coming soon…"), "Purchases")
        tabs.addTab(self._make_placeholder("History timeline coming soon…"), "History")
        tabs.addTab(self._make_placeholder("Analytics coming soon…"), "Analytics")

        # Central container with layout
        panel = QWidget()
        panel.setObjectName("MainPanel")        
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.addWidget(tabs)

        self.setCentralWidget(panel)

    def _make_placeholder(self, text: str) -> QWidget:
        """
        Build a placeholder widget with a centered label.

        Args:
            text: The text to display in the placeholder QLabel.

        Returns:
            QWidget containing a vertical layout with a single QLabel.
        """
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel(text))
        return w

    def open_users_dialog(self) -> None:
        dlg = UsersDialog(self)
        dlg.exec()

    def _current_theme_mode(self) -> str:
        """Read saved theme mode from QSettings. Defaults to 'light'."""
        settings = QSettings()
        return settings.value("appearance/mode", "light")

    def _apply_theme(self, mode: str) -> None:
        """
        Apply light/dark QSS to the whole app and persist choice.
        """
        # Persist
        settings = QSettings()
        settings.setValue("appearance/mode", mode)

        # Load QSS
        # styles directory is at src/styles relative to this file
        styles_dir = Path(__file__).resolve().parent.parent / "styles"
        qss_file = styles_dir / f"rounded_{'dark' if mode == 'dark' else 'light'}.qss"
        qss = qss_file.read_text(encoding="utf-8") if qss_file.exists() else ""

        # Apply to the whole application
        app = self.window().windowHandle().screen().virtualSiblings()  # not needed; just illustrating scope
        self.window().windowHandle()  # noop; ensures window exists

        # Simpler: just set on QApplication
        from PySide6.QtWidgets import QApplication
        QApplication.instance().setStyleSheet(qss)

        # Keep menu checkmarks in sync if changed elsewhere
        if hasattr(self, "act_light") and hasattr(self, "act_dark"):
            self.act_light.setChecked(mode == "light")
            self.act_dark.setChecked(mode == "dark")

