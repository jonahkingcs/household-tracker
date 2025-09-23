"""
users_dialog.py

Dialog window for managing household users.

Provides a simple table interface where:
- All users are listed with their name and an "Active" checkbox.
- Users can be added via an "Add User…" button.
- Toggling the "Active" checkbox marks a user in/out of rotations.

Data persistence:
- Reads/writes users using repository helpers in src.db.repo.users.
- Uses SessionLocal for scoped database sessions.

Intended usage:
- Accessed from MainWindow under Settings → Users.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.db.repo.users import create_user, list_users, set_active
from src.db.session import SessionLocal


class UsersDialog(QDialog):
    """The users management dialog.

    Displays a two-column table with:
    - User name (read-only text)
    - Active status (checkbox)

    Also provides an "Add User…" button and Close button.
    """
    COL_NAME = 0        # Column index for the user name cell
    COL_ACTIVE = 1      # Column index for the active checkbox cell

    def __init__(self, parent: QWidget | None = None) -> None:
        """
        Initialize the dialog UI:
        - Build the QTableWidget with two columns.
        - Configure table appearance and selection behavior.
        - Add "Add User…" button and a standard Close button.
        - Connect signals to slots.
        - Populate the table with current users.
        """

        super().__init__(parent)
        self.setWindowTitle("Users")
        self.resize(520, 360)

        # Create table with 2 columns (Name, Active)
        self.table = QTableWidget(0, 2, self)
        self.table.setHorizontalHeaderLabels(["Name", "Active"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)  # names read-only for now

        # Hide the row numbers on the left
        self.table.verticalHeader().setVisible(False)

        # Nicer row height and interactive sizing
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.horizontalHeader().setHighlightSections(False)

        # Row selection + no inline editing of names (you already set NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)

        # Show grid and alternating rows
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)

        # Buttons
        self.btn_add = QPushButton("Add User…")
        self.btn_add.clicked.connect(self.on_add_user)

        close_box = QDialogButtonBox(QDialogButtonBox.Close)
        close_box.rejected.connect(self.reject)

        # Layout
        top = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(self.btn_add)
        row.addStretch(1)
        
        # Wrap the table in a rounded panel

        top.addLayout(row)
        top.addWidget(self.table)
        top.addWidget(close_box)

        # Signals
        self.table.itemChanged.connect(self.on_item_changed)

        # Initial fill
        self._fill_table()

    # ---------- Data & UI helpers ----------


    def _fill_table(self) -> None:
        """
        Query the database for all users and repopulate the table.

        For each user:
        - Insert a row
        - Display their name (non-editable)
        - Display a checkbox for Active status
        """
        with SessionLocal() as s:
            users = list_users(s)

        # Temporarily block itemChanged signal while repopulating,
        # so toggles don't accidentally trigger DB writes.
        self.table.blockSignals(True)
        try:
            self.table.setRowCount(0)
            for u in users:
                r = self.table.rowCount()
                self.table.insertRow(r)

                # Name (read-only)
                name_item = QTableWidgetItem(u.name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                # Store the user id on the name cell (used when toggling)
                name_item.setData(Qt.UserRole, u.id)
                self.table.setItem(r, self.COL_NAME, name_item)

                # Active checkbox
                active_item = QTableWidgetItem()
                active_item.setFlags(
                    Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
                    )
                active_item.setCheckState(Qt.Checked if u.active else Qt.Unchecked)
                self.table.setItem(r, self.COL_ACTIVE, active_item)
        finally:
            self.table.blockSignals(False)

    # ---------- Slots ----------

    def on_add_user(self) -> None:
        """
        Prompt for a new user name and insert into DB as active.

        Rebuilds the table after creation so the new user is visible immediately.
        """
        name, ok = QInputDialog.getText(self, "Add User", "Name:")
        if not ok:
            return
        name = name.strip()
        if not name:
            return
        with SessionLocal() as s:
            create_user(s, name=name)
        self._fill_table()

    def on_item_changed(self, item: QTableWidgetItem) -> None:
        """
        Handle checkbox toggles in the 'Active' column.

        When a checkbox is toggled:
        - Look up the corresponding user_id from the row's Name cell.
        - Write the new active state to the database.
        """
        if item.column() != self.COL_ACTIVE:
            return  # Ignore edits in other columns

        row = item.row()
        name_item = self.table.item(row, self.COL_NAME)
        user_id = name_item.data(Qt.UserRole)
        is_active = item.checkState() == Qt.Checked

        with SessionLocal() as s:
            set_active(s, user_id=user_id, active=is_active)