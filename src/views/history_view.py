"""
history_view.py — Read-only Purchases History with filters + custom table chrome.

What this file provides
-----------------------
- A QTableView backed by a minimal QAbstractTableModel to list purchase history.
- Three filters (Item, Buyer, Date range) with a Refresh/Clear UX.
- Custom “pixel” chrome:
    * Thick cell grid (ThickGridDelegate)
    * Rounded pixel border overlay (PixelTableOverlay)
    * Extra separators under the vertical (row-number) header
"""

from __future__ import annotations

import datetime as dt

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from src.db.repo.items import list_items, list_purchases
from src.db.repo.users import list_users
from src.db.session import SessionLocal
from src.views.history_models import ChoresTableModel
from src.views.pixel_table_overlay import PixelTableOverlay
from src.views.thick_grid_delegate import ThickGridDelegate
from src.views.vertical_header_painter import VerticalHeaderPainter

# ----- History view (widget) --------------------------------------------------

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
        self.table.setFrameShape(QFrame.NoFrame)            # remove inner frame
        self.table.setAlternatingRowColors(True)            # use QSS alt row color
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setEditTriggers(QTableView.NoEditTriggers)   # read-only
        self.table.setSortingEnabled(True)
        self.table.setShowGrid(False)                       # we draw our own grid

        # The model
        self.model = ChoresTableModel()
        self.table.setModel(self.model)

        # Make the view expand fully with the window
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Column sizing strategy:
        # - Item..Date (0..4) autosize to content
        # - Comments (5) is interactive and will be stretched after data loads
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Interactive)          # default
        for c in range(5):                                       # columns 0..4
            h.setSectionResizeMode(c, QHeaderView.ResizeToContents)

        # prep Comments column; final stretch is applied after data loads
        h.setSectionResizeMode(5, QHeaderView.Interactive)       # temporary
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        # Default sort: Date desc (newest first)
        self.table.sortByColumn(4, Qt.DescendingOrder)

        # Custom chrome:
        # - Rounded pixel outer border overlay (drawn over headers + body)
        # - Thick per-cell grid lines (skip outermost edges)
        self._table_overlay = PixelTableOverlay(self.table, parent=self)
        self.table.setItemDelegate(ThickGridDelegate())
        assert isinstance(self.table.itemDelegate(), ThickGridDelegate)

        # Ensure the overlay snaps to the table after the first layout pass
        QTimer.singleShot(0, self._table_overlay._sync_to_target)

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
        - Buyers: active users only (mirrors dialogs), prefixed with "All buyers".
        - Range: static choices.
        """
        # Items
        self.item_filter.blockSignals(True)
        self.item_filter.clear()
        self.item_filter.addItem("All items", userData=None)
        with SessionLocal() as s:
            for it in list_items(s):
                self.item_filter.addItem(it.name, userData=it.id)
        self.item_filter.blockSignals(False)

        # Buyers (active only; consistent with Add/Edit/Log dialogs)
        self.buyer_filter.blockSignals(True)
        self.buyer_filter.clear()
        self.buyer_filter.addItem("All buyers", userData=None)
        with SessionLocal() as s:
            for u in list_users(s):
                if u.active:
                    self.buyer_filter.addItem(u.name, userData=u.id)
        self.buyer_filter.blockSignals(False)

        # Date ranges
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
        """Reset all filters to their 'All' state and refresh the table."""
        self.item_filter.setCurrentIndex(0)
        self.buyer_filter.setCurrentIndex(0)
        self.range_filter.setCurrentIndex(0)
        self.refresh()

    def refresh(self):
        """
        Query the repository with current filters and update the table model.

        Uses a short-lived SessionLocal for each refresh. After resetting the
        model, we re-apply the default sort (Date desc) because Qt clears the
        sort when the model is reset.
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
        self.model.set_rows(rows)

        # Defer column sizing until after the view has applied the new model & layout
        QTimer.singleShot(0, self._fit_table_to_content)

        # Paint extra horizontal separators under row numbers (skip very bottom)
        self._vhp = VerticalHeaderPainter(self.table)

        # Keep columns fitted when headers resize/scrollbar range changes
        self.table.horizontalHeader().sectionResized.connect(
            lambda *_: self._fit_table_to_content()
            )
        self.table.verticalScrollBar().rangeChanged.connect(lambda *_: self._fit_table_to_content())

        # keep date desc after reset
        self.table.sortByColumn(4, Qt.DescendingOrder)

    def _fit_table_to_content(self):
        """
        Resize the table widget to exactly fit its current content (rows/cols)
        so the rounded overlay hugs the corners (reduces empty space on right/bottom).
        """
        tv = self.table
        model = tv.model()
        if not model:
            return

        # Heights: header + sum of row heights (+ frame/grid breathing)
        hh = tv.horizontalHeader().height()
        rows_h = sum(tv.rowHeight(r) for r in range(model.rowCount()))

        # Widths: vertical header + sum of column widths (+ scrollbar if visible)
        vh_w = tv.verticalHeader().width()
        cols_w = sum(tv.columnWidth(c) for c in range(model.columnCount()))
        fw2 = tv.frameWidth() * 2
        grid = 4    # small fudge factor so the overlay line doesn't clip
        vscroll_w = tv.verticalScrollBar().width() if tv.verticalScrollBar().isVisible() else 0

        # Fix size to content bounds (minimum height guard avoids collapsing when empty)
        tv.setFixedHeight(max(hh + rows_h + fw2 + grid, 140))
        tv.setFixedWidth(vh_w + cols_w + fw2 + vscroll_w + grid)