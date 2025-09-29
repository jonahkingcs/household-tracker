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

import sys
from pathlib import Path

from PySide6.QtCore import QSettings
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget

from src.views.chore_board import ChoreBoard
from src.views.users_dialog import UsersDialog


class MainWindow(QMainWindow):
    """The main top-level window of the Household Tracker application."""

    def __init__(self):
        """
        Initialize the main window and UI chrome.

        Responsibilities:
        - Build menus: Settings (Users…), View → Appearance (Light/Dark).
        - Restore and apply the saved theme via QSettings.
        - Wire up a keyboard shortcut to toggle themes.
        - Construct the central tab widget with placeholder pages (except Chores).
        """
        super().__init__()
        self.setWindowTitle("Household Tracker")
        self.resize(1100, 720)

        # ----- Menu: Settings → Users… -----
        menubar = self.menuBar()
        settings_menu = menubar.addMenu("&Settings")

        act_users = QAction("Users...", self)
        act_users.triggered.connect(self.open_users_dialog)
        settings_menu.addAction(act_users)

        # ----- Menu: View → Appearance → Light / Dark -----
        view_menu = menubar.addMenu("&View")
        appearance_menu = view_menu.addMenu("Appearance")

        # Two checkable actions that behave like radio buttons
        self.act_light = QAction("Light Mode", self, checkable=True)
        self.act_dark = QAction("Dark Mode", self, checkable=True)

        # Exclusive selection (radio behaviour)
        group = QActionGroup(self)
        group.setExclusive(True)
        group.addAction(self.act_light)
        group.addAction(self.act_dark)

        appearance_menu.addAction(self.act_light)
        appearance_menu.addAction(self.act_dark)

        # Restore theme (defaults to 'light') and sync checkmarks
        mode = self._current_theme_mode()   # light or dark
        self._apply_theme(mode)
        self.act_light.setChecked(mode == "light")
        self.act_dark.setChecked(mode == "dark")

        # Apply when toggled ON (avoid double-application when toggled OFF)
        self.act_light.toggled.connect(lambda checked: checked and self._apply_theme("light"))
        self.act_dark.toggled.connect(lambda checked: checked and self._apply_theme("dark"))

        # ----- Keyboard shortcut: toggle light/dark (Shift+L) -----
        # Note: using a single-key chord for fast switching while testing.
        # If you later want an app-wide shortcut regardless of focus, consider:
        #   toggle_act.setShortcutContext(Qt.ApplicationShortcut)
        toggle_act = QAction("Toggle Light/Dark", self)
        if sys.platform == "darwin":
            toggle_act.setShortcut(QKeySequence("Shift+L"))
        else:
            toggle_act.setShortcut(QKeySequence("Shift+L"))
        toggle_act.setShortcutVisibleInContextMenu(True)
        toggle_act.triggered.connect(self._toggle_theme)

        view_menu.addSeparator()
        view_menu.addAction(toggle_act)

        # Register on the window so the shortcut works even if menu isn't open
        self.addAction(toggle_act)
        self._act_toggle_theme = toggle_act # keep a reference

        # ----- Central content: tab widget -----
        tabs = QTabWidget()
        tabs.addTab(ChoreBoard(self), "Chores") # real board
        tabs.addTab(self._make_placeholder("Purchases board coming soon…"), "Purchases")
        tabs.addTab(self._make_placeholder("History timeline coming soon…"), "History")
        tabs.addTab(self._make_placeholder("Analytics coming soon…"), "Analytics")

        # Main content panel (allows consistent padding around tabs)
        panel = QWidget()
        panel.setObjectName("MainPanel")        
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(12, 12, 12, 12)
        panel_layout.addWidget(tabs)
        self.setCentralWidget(panel)

    # ----- Small UI helpers -------------------------------------------------

    def _make_placeholder(self, text: str) -> QWidget:
        """
        Build a simple placeholder page with a centered label.

        Args:
            text: The message to show in the placeholder page.
        """
        w = QWidget()
        v = QVBoxLayout(w)
        v.addWidget(QLabel(text))
        return w

    def open_users_dialog(self) -> None:
        """Open the Users dialog for add/delete/activate/inactivate operations."""
        dlg = UsersDialog(self)
        dlg.exec()

    # ----- Theme persistence & application ----------------------------------

    def _current_theme_mode(self) -> str:
        """
        Read the saved theme mode from QSettings.

        Returns:
            "light" or "dark". Defaults to "light" if no value has been stored.
        """
        settings = QSettings()
        return settings.value("appearance/mode", "light")

    def _apply_theme(self, mode: str) -> None:
        """
        Apply the chosen theme (light/dark) and persist the selection.

        - Saves the mode under key 'appearance/mode' using QSettings.
        - Loads the corresponding QSS file from src/styles/.
        - Applies the stylesheet to the entire QApplication.
        - Updates menu checkmarks to reflect the active theme.
        """
        # Persist user preference
        settings = QSettings()
        settings.setValue("appearance/mode", mode)

        # Resolve and load the theme stylesheet
        styles_dir = Path(__file__).resolve().parent.parent / "styles"
        qss_file = styles_dir / f"rounded_{'dark' if mode == 'dark' else 'light'}.qss"
        qss = qss_file.read_text(encoding="utf-8") if qss_file.exists() else ""

        # Apply to the whole application
        # (Ensuring the window handle exists is a no-op safety line.)
        self.window().windowHandle()  # noop; ensures window exists
        from PySide6.QtWidgets import QApplication
        QApplication.instance().setStyleSheet(qss)

        # Keep menu checkmarks in sync if changed programmatically (e.g., shortcut)
        if hasattr(self, "act_light") and hasattr(self, "act_dark"):
            self.act_light.setChecked(mode == "light")
            self.act_dark.setChecked(mode == "dark")

    def _toggle_theme(self) -> None:
        """
        Flip between light and dark themes.

        Used by the keyboard shortcut and can be reused for other toggles.
        """
        mode = self._current_theme_mode()
        self._apply_theme("dark" if mode == "light" else "light")

