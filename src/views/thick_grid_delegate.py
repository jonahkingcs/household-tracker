"""
thick_grid_delegate.py — Paint thick pixel grid lines between QTableView cells.

Purpose
-------
Qt's built-in table grid is 1px and not easily stylable per-edge. This delegate
draws our own cell dividers in a specific colour/thickness, while *skipping*
the outermost right/bottom edges so the rounded overlay (PixelTableOverlay)
can own the outer frame.

How it works
------------
- Let the default item painting run first (text, backgrounds, selection).
- Then draw two rectangles per cell:
  * a vertical strip at the right edge (column separator)
  * a horizontal strip at the bottom edge (row separator)
- On the last column/last row we **skip** drawing to avoid double borders.
- Antialiasing is disabled so the lines look crisp/pixelated.

Usage
-----
table.setItemDelegate(ThickGridDelegate())
"""

from PySide6.QtCore import QRect
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem

# Grid appearance (match QSS + overlay colour)
GRID_COLOUR = QColor("#cfe8cf")
GRID_W = 2  # thickness in device pixels

class ThickGridDelegate(QStyledItemDelegate):
    """Custom delegate that paints thick right/bottom dividers for each cell."""

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """
        Draw default cell content, then add grid lines.

        Draw:
          - Right divider: for all columns except the last
          - Bottom divider: for all rows except the last

        Skipping the last row/column prevents the inner grid from overlapping
        the outer rounded border drawn by PixelTableOverlay.
        """
        # 1) Let Qt paint the default cell visuals (selection bg, text, etc.)
        super().paint(painter, option, index)

        # Model dimensions to detect last row/column
        rows = index.model().rowCount()
        cols = index.model().columnCount()
        is_last_col = index.column() == cols - 1
        is_last_row = index.row() == rows - 1

        # The pixel rect for the current cell
        r = option.rect
        painter.save()
        try:
            # Keep lines crisp (no anti-aliased blur)
            painter.setRenderHint(QPainter.Antialiasing, False)

            # ---- Right divider (between columns) ---------------------------
            # Draw only if this is NOT the last column (outer frame owns that edge)
            if not is_last_col:
                # Position the strip so it sits "inside" the cell
                rx = r.right() - (GRID_W - 1)
                painter.fillRect(QRect(rx, r.top(), GRID_W, r.height()+1), GRID_COLOUR)

            # ---- Bottom divider (between rows) -----------------------------
            # Draw only if this is NOT the last row (outer frame owns that edge)
            if not is_last_row:
                by = r.bottom() - (GRID_W - 1)
                painter.fillRect(QRect(r.left(), by, r.width()+1, GRID_W), GRID_COLOUR)
                
        finally:
            painter.restore()
