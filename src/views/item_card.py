"""
ItemCard — card UI for one recurring purchase item.

Overview
--------
- Visual card used on the Purchases board (2 per row like ChoreCard).
- Shows: title, optional description, humanized restock due, next buyer, and actions.
- Actions: "Purchase…" and "Edit…" emit signals back to the parent view.

Styling
-------
- Uses objectName 'ItemCard' so QSS can apply the pixel 9-slice border/background.
- Description and meta labels expose properties ('itemDesc', 'itemMeta') for QSS.
- Height is fixed (CARD_H) so rows stay aligned; width expands within the grid cell.

Signals
-------
- purchaseClicked(item_id: str): emitted when the Purchase button is pressed.
- editClicked(item_id: str):     emitted when the Edit button is pressed.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

# Uniform height so cards in the same row align neatly.
CARD_H = 200

class ItemCard(QWidget):
    """UI card for a single recurring item with title, meta, and actions."""

    # Signals carry the item's id so the parent view can act on it.
    purchaseClicked = Signal(str)  # item_id
    editClicked = Signal(str)      # item_id

    def __init__(
            self,
            item_id: str,
            name: str,
            description: str,
            due_text: str,
            buyer_text: str,
            parent=None
        ) -> None:
        """
        Build the card UI.

        Args:
            item_id: Identifier for the item (propagated via signals).
            name: Item name shown as the card title.
            description: Optional details (brand notes, size, etc.).
            due_text: Humanized next restock date (e.g., "Today", "in 3d").
            buyer_text: Display name of the next buyer.
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self.item_id = item_id

        # Enable stylesheet-based rounded/tinted background (pixel 9-slice).
        self.setObjectName("ItemCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Fixed height across cards; width expands within the grid cell.
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(CARD_H)

        # ---- Layout scaffolding ----
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(0) # no default gaps

        # Title + Description grouped with zero spacing
        hdr = QVBoxLayout()
        hdr.setContentsMargins(0, 0, 0, 0)
        hdr.setSpacing(0)

        title = QLabel(name)
        title.setMargin(0)
        title.setContentsMargins(0, 0, 0, 0)
        title.setIndent(0)
        title.setStyleSheet("font-weight: 600; font-size: 14pt; margin: 0; padding: 0;")
        hdr.addWidget(title)

        # Description (optional, soft tone via QSS; wraps if long)
        self._desc = QLabel(description or "")
        self._desc.setWordWrap(True)
        self._desc.setProperty("choreDesc", True)      # was: "itemDesc"
        self._desc.setVisible(bool((description or "").strip()))
        self._desc.setMargin(0)
        self._desc.setContentsMargins(0, 0, 0, 0)
        self._desc.setIndent(0)
        hdr.addWidget(self._desc)

        v.addLayout(hdr)

        # Small gap before meta line
        v.addSpacing(6)

        # Meta line: restock due + next buyer (soft tone via QSS)
        self._meta = QLabel(f"Restock: {due_text}  •  Next buyer: {buyer_text}")
        self._meta.setProperty("choreMeta", True)      # was: "itemMeta"
        self._meta.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self._meta)

        # Actions row: Purchase / Edit
        row = QHBoxLayout()
        btn_purchase = QPushButton("Purchase…")
        btn_edit     = QPushButton("Edit…")
        row.addWidget(btn_purchase)
        row.addStretch(1)   # push Edit to the far right
        row.addWidget(btn_edit)
        v.addLayout(row)

        # Wire actions to signals, carrying the item id.
        btn_purchase.clicked.connect(lambda: self.purchaseClicked.emit(self.item_id))
        btn_edit.clicked.connect(lambda: self.editClicked.emit(self.item_id))

    def update_meta(self, *, due_text: str, buyer_text: str) -> None:
        """Refresh the meta line (due and next buyer) without rebuilding the card."""
        self._meta.setText(f"Restock: {due_text}  •  Next buyer: {buyer_text}")