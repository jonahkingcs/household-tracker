"""
vertical_header_painter.py — add custom grid lines to the *row-number* header.

Why?
----
Qt's stylesheet can't target "only the last header section". I want thick
horizontal separators under each row number, but NOT under the *last* one so
the rounded outer border (PixelTableOverlay) owns the very bottom edge.

What it does
------------
- Installs an event filter on the vertical header's *viewport*.
- After Qt paints the default header labels, we draw 2px lines at the bottom
  of each section (row), skipping the last section.

Usage
-----
from src.views.vertical_header_painter import VerticalHeaderPainter
self._vhp = VerticalHeaderPainter(self.table)
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRect
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import QTableView

# Match the app-wide grid color and thickness
GRID = QColor("#cfe8cf")
W = 2  # line thickness in device pixels

class VerticalHeaderPainter(QObject):
    """
    Draw 2px horizontal lines across the *vertical header* (row numbers),
    skipping the last section so the outer rounded border is the only bottom line.
    """

    def __init__(self, table: QTableView):
        """
        Hook into the vertical header's viewport so we can paint after Qt.

        Args:
            table: The QTableView whose left-side (vertical) header we augment.
        """
        # Parent this object to the header viewport so it lives as long as it
        super().__init__(table.verticalHeader().viewport())
        self.table = table

        # We need events from the *viewport* (the part that actually paints)
        table.verticalHeader().viewport().installEventFilter(self)

    def eventFilter(self, obj, ev):
        """
        On each repaint of the vertical header viewport, let Qt draw first,
        then overlay our custom separators under each section except the last.
        """
        # Only react to paint events coming from the v-header viewport
        if obj is self.table.verticalHeader().viewport() and ev.type() == QEvent.Paint:
            # Allow the default header (numbers, background) to be painted
            ok = super().eventFilter(obj, ev)  # let Qt draw labels first

            # If there are no rows, nothing to draw
            rows = self.table.model().rowCount()
            if rows <= 0:
                return ok
            
            vp = obj.rect()     # viewport rectangle in its own coordinates

            p = QPainter(obj)
            try:
                # Keep pixels crisp to match the rest of the grid
                p.setRenderHint(QPainter.Antialiasing, False)
                p.setPen(GRID)
                p.setBrush(GRID)

                # Walk down the header, accumulating section heights
                y = 0
                for r in range(rows):
                    y += self.table.rowHeight(r)
                    # Draw a separator at the bottom of this section,
                    # but skip the last section so the outer overlay owns it.
                    if r < rows - 1:  # skip last one
                        p.fillRect(QRect(vp.left(), y - (W - 1), vp.width(), W), GRID)
            finally:
                p.end()
            return ok
        
        # Not our target widget/event - pass through
        return super().eventFilter(obj, ev)
