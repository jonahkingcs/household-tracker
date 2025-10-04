"""
AddItemDialog — Create a new recurring purchase item.

Overview
--------
Simple modal dialog that collects:
- Item name (required)
- Description (optional, multi-line)
- Restock frequency in days (required, int)
- First buyer (active users only)

On Save, the item is created via repo.create_item() and the dialog closes
with accept(). If there are no active users, we warn and close immediately.

Styling
-------
- Frequency QSpinBox arrows are hidden (we use a flat design with custom
  QSS arrows elsewhere).
- The dialog width is slightly larger to make the description field comfortable.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractSpinBox,
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

from src.db.repo.items import create_item
from src.db.repo.users import list_users
from src.db.session import SessionLocal


class AddItemDialog(QDialog):
    """Modal dialog for creating a new recurring purchase item."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Add Item")
        self.setMinimumWidth(520)  # widen to make multi-line description comfortable

        # ---- Layout scaffolding (outer VBox + inner Form) ----
        v = QVBoxLayout(self)
        form = QFormLayout()
        v.addLayout(form)

        # ---- Name (required, 1-line) ----
        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("e.g., Toilet Paper")
        form.addRow("Name:", self.txt_name)

        # ---- Description (optional, multi-line) ----
        self.txt_desc = QTextEdit()
        self.txt_desc.setPlaceholderText("Optional")
        self.txt_desc.setFixedHeight(60)  # ~2 lines tall
        form.addRow("Description:", self.txt_desc)

        # ---- Frequency (days) ----
        self.spn_freq = QSpinBox()
        self.spn_freq.setRange(1, 365)         # reasonable bounds for a recurring restock
        self.spn_freq.setValue(14)             # fortnightly default
        # Use flat look (arrows styled globally in QSS)
        self.spn_freq.setButtonSymbols(QAbstractSpinBox.NoButtons)  # hide native arrows
        form.addRow("Frequency (days):", self.spn_freq)

        # ---- First buyer (active users only) ----
        self.cmb_user = QComboBox()
        with SessionLocal() as s:
            # Filter to active users so rotations make sense immediately
            users = [u for u in list_users(s) if u.active]
            if not users:
                # No valid assignees — notify and exit early
                QMessageBox.warning(self, "No Users", "Add an active user first.")
                self.reject()
                return
            # Populate combo: show name, stash id in item data
            for u in users:
                # Store the user id as item data for easy retrieval on save
                self.cmb_user.addItem(u.name, u.id)
        form.addRow("First buyer:", self.cmb_user)

        # ---- Dialog buttons (Save/Cancel) ----
        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.accepted.connect(self._on_save) # validate + persist
        box.rejected.connect(self.reject)   # close without saving
        v.addWidget(box)

    # ---------- Slots ----------

    def _on_save(self) -> None:
        """
        Validate inputs and create the item.

        - Name must be non-empty.
        - Description is optional (trimmed).
        - Frequency from spinbox.
        - First buyer is the combo’s currentData() (user_id).

        On success, accept() to close the dialog.
        """
        name = self.txt_name.text().strip()
        desc = self.txt_desc.toPlainText().strip()  # optional (may be "")
        freq = self.spn_freq.value()
        buyer_id = self.cmb_user.currentData()

        # Basic validation
        if not name:
            QMessageBox.warning(self, "Validation", "Please enter an item name.")
            return

        # Persist to DB via repository
        try:
            with SessionLocal() as s:
                create_item(
                    s,
                    name=name,
                    description=desc,
                    frequency_days=freq,
                    first_buyer_id=buyer_id,
                )
        except Exception as e:
            # Bubble up any DB errors to the user (unique constraints, etc.)
            QMessageBox.critical(self, "Failed to add item", str(e))
            return

        # Close the dialog with success
        self.accept()
