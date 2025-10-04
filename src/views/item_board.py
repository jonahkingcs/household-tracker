"""
item_board.py — Scrollable grid of ItemCard widgets with a fixed footer.

Overview
--------
- Displays items as rounded "cards" in a 2-column grid inside a QScrollArea.
- Each card shows name, optional description, next restock, next buyer,
  and has actions: Purchase… / Edit….
- A non-scrolling footer at the bottom-left provides an "Add Item" button.

Data flow
---------
- Items are read via repo.list_items(SessionLocal()).
- Purchasing/editing/adding opens dialogs; on accept, the grid is refreshed.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.db.repo.items import list_items
from src.db.session import SessionLocal
from src.services.dates import humanize_due
from src.views.add_item_dialog import AddItemDialog
from src.views.edit_item_dialog import EditItemDialog
from src.views.item_card import ItemCard
from src.views.log_purchase_dialog import LogPurchaseDialog


def _buyer_label(item) -> str:
    """Return the next buyer's display name or 'Unassigned' if missing."""
    return item.next_buyer.name if getattr(item, "next_buyer", None) else "Unassigned"


class ItemBoard(QWidget):
    """Items board widget.

    Structure:
        [ QScrollArea (fills available space)
            -> QFrame content
                -> QGridLayout (2 columns of ItemCard widgets)
        ]
        [ Footer (non-scrolling): "Add Item" button left-aligned ]

    Notes:
    - Columns are set to equal stretch so two cards fill the row and meet in the middle.
    - Cards have fixed height (handled by ItemCard) but expand horizontally to share the row.
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        # Root layout for the board
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # --- Scroll area: holds the grid of item cards; no outer border/background
        self.area = QScrollArea(self)
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.NoFrame)
        self.area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        root.addWidget(self.area)

        # --- Content inside the scroller: borderless frame + 2-column grid
        self.content = QFrame()
        self.content.setFrameShape(QFrame.NoFrame)
        self.content.setStyleSheet("QFrame { border: none; background: transparent; }")

        self.grid = QGridLayout(self.content)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)

        # Two equal-width columns that stretch to fill the row
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)

        # Put the content into the scroll area
        self.area.setWidget(self.content)

        # --- Footer (fixed, non-scrolling): Add Item button at bottom-left
        footer = QHBoxLayout()
        self.btn_add = QPushButton("Add Item")
        self.btn_add.clicked.connect(self._on_add_item)
        footer.addWidget(self.btn_add)  # pinned to the left
        footer.addStretch(1)            # room for future controls on the right
        root.addLayout(footer)

        # Initial population of grid
        self.refresh()

    # ---------- Helpers ----------

    def _clear_grid(self) -> None:
        """Remove all widgets/items from the grid layout."""
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                # Detach widget from layout; Qt will delete later
                w.setParent(None)

    def refresh(self) -> None:
        """Rebuild the grid from the current items in the database."""
        self._clear_grid()

        # Query items once; SessionLocal context ensures proper closing
        with SessionLocal() as s:
            items = list_items(s)

        # Lay out cards two per row
        for i, it in enumerate(items):
            r = i // 2
            c = i % 2
            due_text = humanize_due(it.next_restock_date)

            # Build a card for this item
            card = ItemCard(
                it.id,
                it.name,
                it.description or "",
                due_text,
                _buyer_label(it),
            )

            # Hook up actions so the board can respond
            card.purchaseClicked.connect(self._on_purchase)
            card.editClicked.connect(self._on_edit)

            # Let the card fill its cell; equal column stretch makes them meet in the middle
            self.grid.addWidget(card, r, c)

    # ---------- Slots (UI actions) ----------

    def _on_add_item(self) -> None:
        """Open the 'Add Item' dialog; on success, refresh the board."""
        dlg = AddItemDialog(self)
        if dlg.exec():
            self.refresh()

    def _on_edit(self, item_id: str) -> None:
        """Open the 'Edit Item' dialog; on success, refresh the board."""
        dlg = EditItemDialog(item_id, self)
        if dlg.exec():
            self.refresh()

    def _on_purchase(self, item_id: str) -> None:
        """Open the 'Log Purchase' dialog; on success, refresh the board."""
        dlg = LogPurchaseDialog(item_id, self)
        if dlg.exec():
            self.refresh()
