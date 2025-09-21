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

from PySide6.QtWidgets import QLabel, QMainWindow, QTabWidget, QVBoxLayout, QWidget
from PySide6.QtGui import QAction

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
