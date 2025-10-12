from __future__ import annotations

import datetime as dt

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from src.db.models import PurchaseRecord
from src.db.repo.items import list_items, list_purchases
from src.db.repo.users import list_users
from src.db.session import SessionLocal


def _fmt_money_pounds(cents: int | None) -> str:
    """
    Format an integer number of cents into a '£x.xx' string.

    Args:
        cents: Amount in minor units (pennies). May be None.

    Returns:
        A human-readable currency string (e.g., '£4.50').
    """
    return f"£{(cents or 0)/100:.2f}"


class PurchasesTableModel(QAbstractTableModel):
    """
    Table model for displaying PurchaseRecord rows in a QTableView.

    Columns:
        0: Item name
        1: Buyer name
        2: Quantity
        3: Total price (formatted, £)
        4: Purchase timestamp (YYYY-MM-DD HH:MM)
        5: Comments
    """

    HEADERS = ["Item", "Buyer", "Qty", "Total", "Date", "Comments"]

    def __init__(self):
        super().__init__()
        # Backing store: materialized ORM entities eager-loaded with .item and .user.
        self._rows: list[PurchaseRecord] = []

    # ---- Qt model API ----

    def rowCount(self, parent=QModelIndex()) -> int:
        """Number of records shown in the table."""
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        """Fixed number of columns as defined by HEADERS."""
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """Return user-facing column headers for the horizontal header."""
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        # For vertical headers (row numbers), show 1-based indices.
        return section + 1

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        """
        Return the cell value for the given model index.

        We only provide DisplayRole data since the view is read-only.
        """
        if not index.isValid():
            return None
        rec = self._rows[index.row()]

        if role == Qt.DisplayRole:
            c = index.column()
            if c == 0:
                # Item name (gracefully handle missing relations)
                return rec.item.name if rec.item else "—"
            if c == 1:
                # Buyer name
                return rec.user.name if rec.user else "—"
            if c == 2:
                # Quantity purchased
                return rec.quantity
            if c == 3:
                # Total price (format minor units → pounds)
                return _fmt_money_pounds(rec.total_price_cents)
            if c == 4:
                # Exact timestamp for auditing / ordering
                return rec.date_purchased.strftime("%Y-%m-%d %H:%M")
            if c == 5:
                # Optional comment text
                return rec.comments or ""
        return None

    # ---- helpers ----

    def set_rows(self, rows: list[PurchaseRecord]):
        """
        Replace the table's dataset with the given records.

        Uses beginResetModel()/endResetModel() to notify the view efficiently.
        """
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()


class HistoryView(QWidget):
    """
    Read-only Purchases History with filters.

    Design notes:
    - Structured to expand later into a type toggle (Purchases | Chores).
    - For now, only Purchases are shown.
    - Filters: by Item, Buyer, and Date range (All / Last 30 / Last 90 days).
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        # --- Top filter row ---------------------------------------------------
        self.item_filter = QComboBox()  # filter by specific Item (or All)
        self.buyer_filter = QComboBox() # filter by buyer (active users)
        self.range_filter = QComboBox() # All time / Last 30 days / Last 90 days
        self.btn_clear = QPushButton("Clear filters")
        self.btn_refresh = QPushButton("Refresh")

        top = QHBoxLayout()
        top.addWidget(QLabel("Item:"))
        top.addWidget(self.item_filter)
        top.addSpacing(12)
        top.addWidget(QLabel("Buyer:"))
        top.addWidget(self.buyer_filter)
        top.addSpacing(12)
        top.addWidget(QLabel("Range:"))
        top.addWidget(self.range_filter)
        top.addStretch(1)                   # push buttons to the right
        top.addWidget(self.btn_clear)
        top.addWidget(self.btn_refresh)

        # --- Table view -------------------------------------------------------
        self.table = QTableView()
        self.table.setAlternatingRowColors(True)                # uses QSS alt row color
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setEditTriggers(QTableView.NoEditTriggers)   # read-only
        self.table.setSortingEnabled(True)                      # enable header sorting

        self.model = PurchasesTableModel()
        self.table.setModel(self.model)
        # Default sort: Date (column 4) descending (newest first)
        self.table.sortByColumn(4, Qt.DescendingOrder)  # Date desc

        # --- Layout root ------------------------------------------------------
        root = QVBoxLayout(self)
        root.addLayout(top)
        root.addWidget(self.table)

        # --- Signal wiring ----------------------------------------------------
        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_clear.clicked.connect(self.clear_filters)
        self.item_filter.currentIndexChanged.connect(self.refresh)
        self.buyer_filter.currentIndexChanged.connect(self.refresh)
        self.range_filter.currentIndexChanged.connect(self.refresh)

        # --- Initial population ----------------------------------------------
        self._init_filters()
        self.refresh()

    # ---------- helpers ----------

    def _init_filters(self):
        """
        Populate the filter combos with choices from the database.

        - Items: all items (ordered by name via repo), prefixed with "All items".
        - Buyers: active users only (mirrors your dialogs), prefixed with "All buyers".
        - Range: static choices.
        """
        self.item_filter.blockSignals(True)
        self.item_filter.clear()
        self.item_filter.addItem("All items", userData=None)
        with SessionLocal() as s:
            for it in list_items(s):
                self.item_filter.addItem(it.name, userData=it.id)
        self.item_filter.blockSignals(False)

        # Buyers (active first; mirrors your Add/Edit/Log dialogs)
        self.buyer_filter.blockSignals(True)
        self.buyer_filter.clear()
        self.buyer_filter.addItem("All buyers", userData=None)
        with SessionLocal() as s:
            for u in list_users(s):
                if u.active:
                    self.buyer_filter.addItem(u.name, userData=u.id)
        self.buyer_filter.blockSignals(False)

        # Ranges
        self.range_filter.blockSignals(True)
        self.range_filter.clear()
        self.range_filter.addItems(["All time", "Last 30 days", "Last 90 days"])
        self.range_filter.blockSignals(False)

    def _date_bounds(self) -> tuple[dt.datetime | None, dt.datetime | None]:
        """
        Compute the (date_from, date_to) tuple for the current range selection.

        Returns:
            (from, to) where:
              - from is inclusive (>=)
              - to is exclusive (<)
            Either may be None for open-ended ranges.
        """
        choice = self.range_filter.currentText()
        now = dt.datetime.utcnow()
        if choice == "Last 30 days":
            return now - dt.timedelta(days=30), None
        if choice == "Last 90 days":
            return now - dt.timedelta(days=90), None
        return None, None

    def clear_filters(self):
        """
        Reset all filters to their 'All' state and refresh the table.
        """
        self.item_filter.setCurrentIndex(0)
        self.buyer_filter.setCurrentIndex(0)
        self.range_filter.setCurrentIndex(0)
        self.refresh()

    def refresh(self):
        """
        Query the repository with current filters and update the table model.

        Uses a short-lived SessionLocal for each refresh. After resetting the
        model, we re-apply the default sort (Date desc) as Qt clears sorting
        on model resets.
        """
        item_id = self.item_filter.currentData()
        user_id = self.buyer_filter.currentData()
        date_from, date_to = self._date_bounds()

        # Pull records from repo; list_purchases eager-loads .item and .user.
        with SessionLocal() as s:
            rows = list_purchases(
                s,
                item_id=item_id,
                user_id=user_id,
                date_from=date_from,
                date_to=date_to,
                order_desc=True,
            )

        # Populate the model and keep the table sorted newest-first.
        self.model.set_rows(rows)
        # keep date desc after reset
        self.table.sortByColumn(4, Qt.DescendingOrder)
