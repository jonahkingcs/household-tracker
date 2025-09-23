"""
complete_chore_dialog.py — Dialog to log a chore completion.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from src.db.repo.chores import complete_chore, get_chore
from src.db.repo.users import list_users
from src.db.session import SessionLocal


class CompleteChoreDialog(QDialog):
    def __init__(self, chore_id: str, parent=None):
        super().__init__(parent)
        self.chore_id = chore_id
        self.setWindowTitle("Complete Chore")

        v = QVBoxLayout(self)
        form = QFormLayout()
        v.addLayout(form)

        # Who did it
        self.cmb_who = QComboBox()
        with SessionLocal() as s:
            users = list_users(s)
            # populate combo with all users (active first would be nice later)
            for u in users:
                self.cmb_who.addItem(u.name, u.id)
            # default: next assignee if present
            chore = get_chore(s, chore_id)
            if chore and chore.next_assignee_id:
                idx = self.cmb_who.findData(chore.next_assignee_id)
                if idx >= 0:
                    self.cmb_who.setCurrentIndex(idx)
        form.addRow("Who:", self.cmb_who)

        # Duration minutes
        self.spn_minutes = QSpinBox()
        self.spn_minutes.setRange(0, 10000)
        self.spn_minutes.setValue(0)
        form.addRow("Duration (min):", self.spn_minutes)

        # Comments
        self.txt_comments = QTextEdit()
        self.txt_comments.setPlaceholderText("Comments (optional)…")
        form.addRow("Comments:", self.txt_comments)

        # Buttons
        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.accepted.connect(self._on_save)
        box.rejected.connect(self.reject)
        v.addWidget(box)

    def _on_save(self):
        who_id = self.cmb_who.currentData()
        minutes = self.spn_minutes.value()
        comments = self.txt_comments.toPlainText().strip()

        with SessionLocal() as s:
            complete_chore(
                s, self.chore_id, who_user_id=who_id, duration_minutes=minutes, comments=comments
                )
        self.accept()
