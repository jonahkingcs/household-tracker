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
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from src.db.repo.chores import list_chores, list_completions
from src.db.repo.items import list_items, list_purchases
from src.db.repo.users import list_users
from src.db.session import SessionLocal
from src.views.history_models import ChoresTableModel, PurchasesTableModel
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

        self._mode = "purchases"

        # --- Top filter row ---------------------------------------------------
        self.item_filter = QComboBox()  # filter by specific Item (or All)
        self.buyer_filter = QComboBox() # filter by buyer (active users)
        self.range_filter = QComboBox() # All time / Last 30 days / Last 90 days
        self.btn_clear = QPushButton("Clear filters")
        self.btn_refresh = QPushButton("Refresh")

        # -- Mode toggle (left side): Purchases | Chores
        self.rb_purchases = QRadioButton("Purchases")
        self.rb_chores = QRadioButton("Chores")
        self.rb_purchases.setChecked(True)  # default

        self.mode_group = QButtonGroup(self)
        self.mode_group.addButton(self.rb_purchases)
        self.mode_group.addButton(self.rb_chores)

        top = QHBoxLayout()
        top.addWidget(self.rb_purchases)
        top.addWidget(self.rb_chores)
        top.addSpacing(16)
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
        self.table.setShowGrid(False)                       # draw own grid

        # The model
        self.model = PurchasesTableModel()
        self.table.setModel(self.model)
        self._configure_headers_for_current_model()

        # Make the view expand fully with the window
        self.table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

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
        self.rb_purchases.toggled.connect(lambda checked: checked and self._set_mode("purchases"))
        self.rb_chores.toggled.connect(lambda checked: checked and self._set_mode("chores"))


        # --- Initial population ----------------------------------------------
        self._init_filters()
        self.refresh()


    # ---------- helpers ----------

    def _set_mode(self, mode: str) -> None:
        if mode == self._mode:
            return
        self._mode = mode

        # Swap table model
        if mode == "purchases":
            self.model = PurchasesTableModel()
            self.table.setModel(self.model)
            self._configure_headers_for_current_model()
            self._init_filters_for_purchases()
        else:
            self.model = ChoresTableModel()
            self.table.setModel(self.model)
            self._configure_headers_for_current_model()
            self._init_filters_for_chores()

        # Re-apply delegate & overlay follow-ups
        self.table.setItemDelegate(ThickGridDelegate())
        self._vhp = VerticalHeaderPainter(self.table)

        # Refresh data for the new mode
        self.refresh()

        # Keep overlay aligned
        QTimer.singleShot(0, self._table_overlay._sync_to_target)

    def _configure_headers_for_current_model(self):
        """Size columns based on whichever model is active (purchases or chores)."""
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.Interactive)

        col_count = len(self.model.HEADERS)

        # Fit all but the last column to contents
        for c in range(col_count - 1):
            h.setSectionResizeMode(c, QHeaderView.ResizeToContents)

        # and let the last column (usually Comments) take remaining space.
        h.setSectionResizeMode(col_count - 1, QHeaderView.Interactive)

        # Default sort: Date column index depends on the model
        from src.views.history_models import PurchasesTableModel  # local import to avoid cycles
        if isinstance(self.model, PurchasesTableModel):
            self.table.sortByColumn(4, Qt.DescendingOrder)  # Purchases: Date = col 4
        else:
            self.table.sortByColumn(3, Qt.DescendingOrder)  # Chores:    Date = col 3


    def _init_filters(self):
        if self._mode == "purchases":
            self._init_filters_for_purchases()
        else:
            self._init_filters_for_chores()


    def _init_filters_for_purchases(self):
        # Primary selector label stays "Item:"
        self.item_filter.blockSignals(True)
        self.item_filter.clear()
        self.item_filter.addItem("All items", userData=None)
        with SessionLocal() as s:
            for it in list_items(s):
                self.item_filter.addItem(it.name, userData=it.id)
        self.item_filter.blockSignals(False)

        self._init_buyer_and_range_common()


    def _init_filters_for_chores(self):
        self.item_filter.blockSignals(True)
        self.item_filter.clear()
        self.item_filter.addItem("All chores", userData=None)
        with SessionLocal() as s:
            for ch in list_chores(s):
                self.item_filter.addItem(ch.name, userData=ch.id)
        self.item_filter.blockSignals(False)

        self._init_buyer_and_range_common()


    def _init_buyer_and_range_common(self):
        # Buyer / Who (same data source)
        self.buyer_filter.blockSignals(True)
        self.buyer_filter.clear()
        self.buyer_filter.addItem("All people", userData=None)  # generic label works for both
        with SessionLocal() as s:
            for u in list_users(s):
                if u.active:
                    self.buyer_filter.addItem(u.name, userData=u.id)
        self.buyer_filter.blockSignals(False)

        # Range
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
        date_from, date_to = self._date_bounds()
        user_id = self.buyer_filter.currentData()
        primary_id = self.item_filter.currentData()  # item_id or chore_id depending on mode

        with SessionLocal() as s:
            if self._mode == "purchases":
                rows = list_purchases(
                    s,
                    item_id=primary_id,
                    user_id=user_id,
                    date_from=date_from,
                    date_to=date_to,
                    order_desc=True,
                )
            else:
                rows = list_completions(
                    s,
                    chore_id=primary_id,
                    user_id=user_id,
                    date_from=date_from,
                    date_to=date_to,
                    order_desc=True,
                )

        self.model.set_rows(rows)

        # Re-fit size and keep overlay aligned
        QTimer.singleShot(0, self._fit_table_to_content)
        self._vhp = VerticalHeaderPainter(self.table)


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