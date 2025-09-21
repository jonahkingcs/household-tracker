"""
UsersDialog — simple user management:
- Lists users (name + Active checkbox)
- Add User...
- Toggle active/inactive via checkbox
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QInputDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.db.session import SessionLocal
from src.db.repo.users import list_users, create_user, set_active


class UsersDialog(QDialog):
    COL_NAME = 0
    COL_ACTIVE = 1

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Users")
        self.resize(520, 360)

        # Create table
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

        top.addLayout(row)
        top.addWidget(self.table)
        top.addWidget(close_box)

        # Signals
        self.table.itemChanged.connect(self.on_item_changed)

        # Initial fill
        self._fill_table()

    # ---------- Data & UI helpers ----------


    def _fill_table(self) -> None:
        """Load users from DB and populate the table."""
        with SessionLocal() as s:
            users = list_users(s)

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
                active_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                active_item.setCheckState(Qt.Checked if u.active else Qt.Unchecked)
                self.table.setItem(r, self.COL_ACTIVE, active_item)
        finally:
            self.table.blockSignals(False)

    # ---------- Slots ----------

    def on_add_user(self) -> None:
        """Prompt for a name and add a new active user."""
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
        """Persist checkbox toggles to DB."""
        if item.column() != self.COL_ACTIVE:
            return

        row = item.row()
        name_item = self.table.item(row, self.COL_NAME)
        user_id = name_item.data(Qt.UserRole)
        is_active = item.checkState() == Qt.Checked

        with SessionLocal() as s:
            set_active(s, user_id=user_id, active=is_active)