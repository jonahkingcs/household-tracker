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
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.db.repo.users import create_user, delete_user, list_users, set_active
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

        # Row selection + no inline editing of names
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)

        # Show grid and alternating rows
        self.table.setShowGrid(True)
        self.table.setAlternatingRowColors(True)

        # Buttons
        self.btn_add = QPushButton("Add User…")
        self.btn_add.clicked.connect(self.on_add_user)

        top_row = QHBoxLayout()
        top_row.addWidget(self.btn_add)
        top_row.addStretch(1)

        # Delete + Close
        self.btn_delete = QPushButton("Delete User")
        self.btn_delete.setEnabled(False)   # Disabled until row is selected
        self.btn_delete.clicked.connect(self.on_delete_user)
        close_box = QDialogButtonBox(QDialogButtonBox.Close)
        close_box.rejected.connect(self.reject)

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(self.btn_delete)   # bottom-left
        bottom_row.addStretch(1)
        bottom_row.addWidget(close_box)

        # Layout
        main = QVBoxLayout(self)
        main.addLayout(top_row)
        main.addWidget(self.table)
        main.addLayout(bottom_row)

        # Signals
        self.table.itemChanged.connect(self.on_item_changed)
        # Enable/disable Delete based on selection
        self.table.itemSelectionChanged.connect(self.on_selection_changed)

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

        self.table.blockSignals(True)
        try:
            self.table.setRowCount(0)
            for u in users:
                r = self.table.rowCount()
                self.table.insertRow(r)

                # Name (read-only) + stash user_id in UserRole
                name_item = QTableWidgetItem(u.name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
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

        # After repopulating, refresh delete button state
        self.on_selection_changed()

    # ---------- Slots ----------

    def on_selection_changed(self, *_) -> None:
        """Enable Delete only when a row is selected."""
        has_selection = self.table.currentRow() >= 0
        self.btn_delete.setEnabled(has_selection)

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

    def on_delete_user(self) -> None:
        """
        Hard-delete the selected user after confirmation.
        History remains (user_id set to NULL); chores/items reassign next user if possible.
        """
        row = self.table.currentRow()
        if row < 0:
            return

        name_item = self.table.item(row, self.COL_NAME)
        if not name_item:
            return

        user_name = name_item.text()
        user_id = name_item.data(Qt.UserRole)

        # Confirm
        msg = QMessageBox(self)
        msg.setWindowTitle("Delete User")
        msg.setText(f"Are you sure you want to delete “{user_name}”?")
        msg.setInformativeText("This permanently removes the user.\n \n")
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        msg.setDefaultButton(QMessageBox.No)

        # Hide the icon:
        msg.setIcon(QMessageBox.Icon.NoIcon)

        resp = msg.exec()
        if resp != QMessageBox.Yes:
            return

        with SessionLocal() as s:
            delete_user(s, user_id=user_id)

        self._fill_table()


    def on_item_changed(self, item: QTableWidgetItem) -> None:
        """
        Handle checkbox toggles in the 'Active' column.

        When a checkbox is toggled:
        - Look up the corresponding user_id from the row's Name cell.
        - Write the new active state to the database.
        """
        if item.column() != self.COL_ACTIVE:
            return

        row = item.row()
        name_item = self.table.item(row, self.COL_NAME)
        if not name_item:
            return

        user_id = name_item.data(Qt.UserRole)
        is_active = item.checkState() == Qt.Checked

        with SessionLocal() as s:
            set_active(s, user_id=user_id, active=is_active)
