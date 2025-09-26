"""
edit_chore_dialog.py — Edit a chore's name and frequency (days).
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from src.db.repo.chores import get_chore, update_chore
from src.db.session import SessionLocal


class EditChoreDialog(QDialog):
    """Dialog to edit a chore's name and frequency (days)."""

    def __init__(self, chore_id: str, parent=None) -> None:
        super().__init__(parent)
        self.chore_id = chore_id
        self.setWindowTitle("Edit Chore")
        self.setMinimumWidth(520) # room for description

        v = QVBoxLayout(self)
        form = QFormLayout()
        v.addLayout(form)

        # Fetch current values
        with SessionLocal() as s:
            ch = get_chore(s, chore_id)
        if not ch:
            QMessageBox.critical(self, "Error", "Chore not found.")
            self.reject()
            return

        # Name
        self.txt_name = QLineEdit(ch.name)
        self.txt_name.setPlaceholderText("Chore name")
        form.addRow("Name:", self.txt_name)

        # Frequency (days)
        self.spn_freq = QSpinBox()
        self.spn_freq.setRange(1, 365)          # sane range; adjust if you like
        self.spn_freq.setValue(int(ch.frequency_days or 1))
        self.spn_freq.setButtonSymbols(QAbstractSpinBox.NoButtons)   # hide arrows
        form.addRow("Frequency (days):", self.spn_freq)

        # Description (optional, multi-line)
        self.txt_desc = QTextEdit()
        self.txt_desc.setPlaceholderText("Optional")
        self.txt_desc.setFixedHeight(60)  # ~2 lines
        self.txt_desc.setPlainText(ch.description or "")
        form.addRow("Description:", self.txt_desc)

        # Buttons
        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.accepted.connect(self._on_save)
        box.rejected.connect(self.reject)
        v.addWidget(box)

    def _on_save(self) -> None:
        name = self.txt_name.text().strip()
        freq = self.spn_freq.value()
        desc = self.txt_desc.toPlainText().strip()

        if not name:
            QMessageBox.warning(self, "Validation", "Please enter a name.")
            return

        try:
            with SessionLocal() as s:
                update_chore(s,
                             self.chore_id,
                             name=name,
                             frequency_days=freq,
                             description=desc,
                             )
        except Exception as e:
            QMessageBox.critical(self, "Save Failed", str(e))
            return

        self.accept()
