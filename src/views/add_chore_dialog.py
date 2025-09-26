"""
add_chore_dialog.py — Create a new chore (name, frequency, first assignee).

Overview
--------
Simple modal dialog that:
- Captures a chore name and frequency (days).
- Lets you pick the first assignee from active users.
- On Save, persists the chore via repo.create_chore and closes with accept().

Behavior
--------
- If there are no active users, the dialog warns and closes immediately.
- Validation: name must be non-empty.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from src.db.repo.chores import create_chore
from src.db.repo.users import list_users
from src.db.session import SessionLocal


class AddChoreDialog(QDialog):
    """Modal dialog for creating a new chore."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Chore")
        self.setMinimumWidth(520) # wider popup to make room for the description

        # ---- Layout scaffolding ----
        v = QVBoxLayout(self)
        form = QFormLayout()
        v.addLayout(form)

        # ---- Name ----
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g., Dishes")
        form.addRow("Name:", self.txt_name)

        # ---- Frequency (days) ----
        self.spn_freq = QSpinBox()
        self.spn_freq.setRange(1, 365)
        self.spn_freq.setValue(7)       # default weekly rotation
        form.addRow("Frequency (days):", self.spn_freq)

        # ---- Description (optional, multi-line) ----
        self.txt_desc = QTextEdit()
        self.txt_desc.setPlaceholderText("Optional")  # shows greyed placeholder text
        # Make it ~2 lines tall (simple, readable default)
        self.txt_desc.setFixedHeight(60)
        form.addRow("Description:", self.txt_desc)

        # ---- First assignee (active users only) ----
        self.cmb_user = QComboBox()
        with SessionLocal() as s:
            # Only active users
            users = [u for u in list_users(s) if u.active]
            if not users:
                # No valid assignees — notify and exit early
                QMessageBox.warning(self, "No Users", "Add an active user first.")
                self.reject()
                return
            for u in users:
                self.cmb_user.addItem(u.name, u.id)
        form.addRow("First assignee:", self.cmb_user)

        # ---- Dialog buttons ----
        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.accepted.connect(self._on_save)
        box.rejected.connect(self.reject)
        v.addWidget(box)

    # ---------- Slots ----------

    def _on_save(self):
        """Validate inputs and create the chore; accept dialog on success."""
        name = self.txt_name.text().strip()
        freq = self.spn_freq.value()
        desc = self.txt_desc.toPlainText().strip() # optional (may be "")
        assignee_id = self.cmb_user.currentData()

        # Basic validation
        if not name:
            QMessageBox.warning(self, "Validation", "Please enter a chore name.")
            return

        # Persist to DB
        try:
            with SessionLocal() as s:
                create_chore(
                        s,
                        name=name,
                        description=desc, # pass optional description
                        frequency_days=freq,
                        assignee_id=assignee_id
                    )
        except Exception as e:
            QMessageBox.critical(self, "Failed to add chore", str(e))
            return

        # Close the dialog with success
        self.accept()
