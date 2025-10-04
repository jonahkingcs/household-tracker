"""
LogPurchaseDialog — Record a purchase for an item and advance rotation.

Overview
--------
Simple modal dialog that collects:
- Who bought it (defaults to the item's next buyer if set)
- Quantity (int, >=1)
- Total price (pounds with 2 decimals; we parse to cents)
- Optional comments

On Save:
- Persists via repo.log_purchase()
- Advances next buyer / bumps next restock date (handled in repo)
- Closes with accept()

Styling/UX
----------
- Width matches the other dialogs for consistency.
- Quantity keeps SpinBox arrows; global QSS flattens/stylizes them.
"""

from __future__ import annotations

from PySide6.QtGui import QDoubleValidator
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

from src.db.repo.items import get_item, log_purchase
from src.db.repo.users import list_users
from src.db.session import SessionLocal


def _price_str_to_cents(text: str) -> int:
    """
    Parse a user-entered price string to integer cents.

    Examples:
      "4.50"   -> 450
      "£4.50"  -> 450
      "12"     -> 1200
      "12.3"   -> 1230

    Behavior:
      - Strips currency symbols, commas, spaces.
      - Uses float parsing with rounding to cents.
      - Returns 0 if the field is empty or invalid.
    """
    cleaned = text.replace("£", "").replace(",", "").strip()
    if not cleaned:
        return 0
    try:
        pounds = float(cleaned)
    except ValueError:
        return 0
    return int(round(pounds * 100))


class LogPurchaseDialog(QDialog):
    """Modal dialog for logging a purchase on an existing item."""

    def __init__(self, item_id: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Log Purchase")
        self.setMinimumWidth(520)  # keep consistent dialog width with other modals
        self.item_id = item_id

        # Fetch the item once; used to preselect the "next buyer"
        with SessionLocal() as s:
            item = get_item(s, item_id)
        if not item:
            QMessageBox.critical(self, "Error", "Item not found.")
            self.reject()
            return

        # ---- Layout scaffolding ----
        v = QVBoxLayout(self)
        form = QFormLayout()
        v.addLayout(form)

        # ---- Who bought (defaults to item's next buyer if present) ----
        self.cmb_user = QComboBox()
        with SessionLocal() as s:
            users = [u for u in list_users(s) if u.active]
        for u in users:
            self.cmb_user.addItem(u.name, u.id)

        # Preselect the next buyer to reduce clicks
        if item.next_buyer_id:
            idx = self.cmb_user.findData(item.next_buyer_id)
            if idx >= 0:
                self.cmb_user.setCurrentIndex(idx)
        form.addRow("Who bought:", self.cmb_user)

        # ---- Quantity ----
        self.spn_qty = QSpinBox()
        self.spn_qty.setRange(1, 9999)  # sane bounds; items like eggs, TP, etc.
        self.spn_qty.setValue(1)
        form.addRow("Quantity:", self.spn_qty)

        # ---- Total price (pounds) ----
        self.txt_price = QLineEdit()
        self.txt_price.setPlaceholderText("e.g., 4.50")
        # Accept up to 2 decimals; visual styling handled by QSS
        self.txt_price.setValidator(QDoubleValidator(0.0, 999999.99, 2, self))
        form.addRow("Total price (£):", self.txt_price)

        # ---- Comments (optional) ----
        self.txt_comments = QTextEdit()
        self.txt_comments.setPlaceholderText("Optional")
        self.txt_comments.setFixedHeight(60)  # ~2 lines
        form.addRow("Comments:", self.txt_comments)

        # ---- Dialog buttons ----
        box = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        box.accepted.connect(self._on_save)
        box.rejected.connect(self.reject)
        v.addWidget(box)

    # ---------- Slots ----------

    def _on_save(self) -> None:
        """
        Validate, log the purchase in the DB, and close on success.

        - Converts price to cents for storage.
        - log_purchase() also advances rotation and bumps the due date.
        """
        user_id = self.cmb_user.currentData()
        qty = self.spn_qty.value()
        cents = _price_str_to_cents(self.txt_price.text())
        comments = self.txt_comments.toPlainText().strip()

        try:
            with SessionLocal() as s:
                log_purchase(
                    s,
                    item_id=self.item_id,
                    user_id=user_id,
                    quantity=qty,
                    total_price_cents=cents,
                    comments=comments,
                )
        except Exception as e:
            QMessageBox.critical(self, "Failed to log purchase", str(e))
            return

        self.accept()