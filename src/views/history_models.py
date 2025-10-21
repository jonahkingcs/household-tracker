from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from src.db.models import ChoreCompletion, PurchaseRecord


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
        """Number of records shown in the table (no children, so ignore parent)."""
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        """Fixed number of columns as defined by HEADERS."""
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        """
        Provide headers for the table.

        - Horizontal header: named columns from HEADERS
        - Vertical header: 1-based row numbers
        """
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return section + 1  # vertical header shows 1,2,3,...

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        """
        Return the cell value for the given model index.

        Only provide DisplayRole data since the view is read-only.
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
                # Total price (format minor units -> pounds)
                return _fmt_money_pounds(rec.total_price_cents)
            if c == 4:
                # Exact timestamp for auditing / ordering
                return rec.date_purchased.strftime("%Y-%m-%d %H:%M")
            if c == 5:
                # Optional comment text
                return rec.comments or ""
        return None

    # ---- dataset swap helper ----

    def set_rows(self, rows: list[PurchaseRecord]):
        """
        Replace the table's dataset with the given records.

        Uses beginResetModel()/endResetModel() to notify the view efficiently.
        """
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
    

# ----- Chores history table model -------------------------------------------


class ChoresTableModel(QAbstractTableModel):
    """
    Table model for displaying ChoreCompletion rows.

    Columns:
        0: Chore name
        1: Who (user name)
        2: Minutes (duration)
        3: Date completed (YYYY-MM-DD HH:MM)
        4: Comments
    """
    HEADERS = ["Chore", "Who", "Minutes", "Date", "Comments"]

    def __init__(self):
        super().__init__()
        # Backing store: ORM entities with .chore and .user eager-loaded
        self._rows: list[ChoreCompletion] = []

    # ---- Qt model API ----
    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return section + 1  # 1-based row numbers

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        rec = self._rows[index.row()]
        if role == Qt.DisplayRole:
            c = index.column()
            if c == 0:
                return rec.chore.name if rec.chore else "—"
            if c == 1:
                return rec.user.name if rec.user else "—"
            if c == 2:
                return rec.duration_minutes
            if c == 3:
                return rec.date_completed.strftime("%Y-%m-%d %H:%M")
            if c == 4:
                return rec.comments or ""
        return None

    # ---- dataset swap helper ----
    def set_rows(self, rows: list[ChoreCompletion]):
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
        

# ----- Small helpers ----------------------------------------------------------

def _fmt_money_pounds(cents: int | None) -> str:
    """
    Format an integer number of cents into a '£x.xx' string.

    Args:
        cents: Amount in minor units (pennies). May be None.

    Returns:
        Human-readable currency (e.g., '£4.50').
    """
    return f"£{(cents or 0)/100:.2f}"