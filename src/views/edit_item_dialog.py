"""
EditItemDialog — Edit name/description/frequency of an Item.

Overview
--------
Simple modal dialog that:
- Prefills the current item fields (name, optional description, frequency).
- Validates name (non-empty) on save.
- Persists via repo.update_item and closes with accept().

Styling/UX
----------
- Width matches AddItemDialog for consistency.
- SpinBox arrows hidden (flat look; QSS provides custom arrows globally).
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

from src.db.repo.items import get_item, update_item
from src.db.session import SessionLocal


class EditItemDialog(QDialog):
    """Modal dialog for editing an existing recurring purchase item."""

    def __init__(self, item_id: str, parent=None) -> None:
        """
        Build the dialog and prefill fields from the DB.

        Args:
            item_id: Primary key of the Item to edit.
            parent:  Optional Qt parent.
        """
        super().__init__(parent)
        self.setWindowTitle("Edit Item")
        self.setMinimumWidth(520)  # match AddItemDialog width for visual consistency
        self.item_id = item_id

        # --- Fetch the target item once for initial values ---
        # Use a short-lived session so the dialog stays decoupled from DB state.
        with SessionLocal() as s:
            item = get_item(s, item_id)

        # If the item no longer exists (deleted elsewhere), fail gracefully.
        if not item:
            QMessageBox.critical(self, "Error", "Item not found.")
            self.reject()
            return

        # ---- Layout scaffolding ----
        v = QVBoxLayout(self)
        form = QFormLayout()
        v.addLayout(form)

        # ---- Name (required) ----
        # Keep single-line editing for the title. We validate non-empty on save.
        self.txt_name = QLineEdit(item.name or "")
        form.addRow("Name:", self.txt_name)

        # ---- Description (optional, multi-line) ----
        # Multi-line field; we keep it compact by default (~2 lines).
        self.txt_desc = QTextEdit(item.description or "")
        self.txt_desc.setFixedHeight(60)  # ~2 lines default
        form.addRow("Description:", self.txt_desc)

        # ---- Frequency (days) ----
        # Integer between 1..365; hide native arrows for the flat look (QSS provides custom).
        self.spn_freq = QSpinBox()
        self.spn_freq.setRange(1, 365)
        self.spn_freq.setValue(int(item.frequency_days))
        self.spn_freq.setButtonSymbols(QAbstractSpinBox.NoButtons)  # hide arrows (flat)
        form.addRow("Frequency (days):", self.spn_freq)

        # ---- Dialog buttons ----
        # Standard Save/Cancel row. Save triggers validation + persistence.
        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.accepted.connect(self._on_save)
        box.rejected.connect(self.reject)
        v.addWidget(box)

    # ---------- Slots ----------

    def _on_save(self) -> None:
        """
        Validate inputs and persist the changes; accept dialog on success.

        Flow:
        - Trim/collect current field values.
        - Validate name is non-empty.
        - Call repo.update_item() inside a short-lived session.
        - On error, show a message and keep the dialog open.
        """
        name = self.txt_name.text().strip()
        desc = self.txt_desc.toPlainText().strip()  # optional
        freq = self.spn_freq.value()

        # Basic validation: title must not be empty
        if not name:
            QMessageBox.warning(self, "Validation", "Please enter an item name.")
            return

        # Persist updates (let the repo raise meaningful errors if something goes wrong)
        try:
            with SessionLocal() as s:
                update_item(
                    s,
                    self.item_id,
                    name=name,
                    description=desc,
                    frequency_days=freq,
                )
        except Exception as e:
            QMessageBox.critical(self, "Failed to save", str(e))
            return

        # Close the dialog indicating success
        self.accept()
