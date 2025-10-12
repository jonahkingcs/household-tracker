"""
pixel_table_overlay.py — Draw a rounded pixel border around a QTableView.

- Transparent, click-through overlay that sits on top of the table (headers + body).
- Draws a 4px outer border in #cfe8cf, skipping under the four corner sprites
  so only the curved pixel corners are visible at the edges.
- Follows the table as layouts resize/move.

Usage (after table is added to a layout and has its model set):
    from src.views.pixel_table_overlay import PixelTableOverlay
    self._table_overlay = PixelTableOverlay(self.table, parent=self)
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QTableView, QWidget


class _FollowEvents(QObject):
    """
    Small helper: an event filter that keeps the overlay perfectly aligned with
    its target table. We watch both the table *and* the overlay's parent for
    layout-affecting events (resize/move/show/hide/layout request) and then ask
    the overlay to realign itself.
    """
    def __init__(self, target: QWidget, overlay: QWidget) -> None:
        super().__init__(target)
        self.target = target
        self.overlay = overlay
        self.parent = overlay.parentWidget()

        # Receive events from the target table
        target.installEventFilter(self)
        # and also from the parent that actually positions the overlay.
        if self.parent:
            self.parent.installEventFilter(self)

    def eventFilter(self, obj, ev):
        """On any relevant geometry/layout change, sync the overlay to the table."""
        if obj in (self.target, self.parent) and ev.type() in (
            QEvent.Resize, QEvent.Move, QEvent.Show, QEvent.Hide, QEvent.LayoutRequest
        ):
            self.overlay._sync_to_target()
        return False


class PixelTableOverlay(QWidget):
    """
    Transparent, mouse-through overlay that draws a 4px #cfe8cf border and
    four pixel-corner sprites around a QTableView (headers + body included).

    Notes:
    - We parent to the table's parent so our rect can cover header + viewport.
    - We avoid antialiasing so the pixel artwork stays crisp.
    """
    def __init__(self, table: QTableView, parent: QWidget | None = None) -> None:
        # Parent to the same widget that contains the table (usually the view's layout)
        super().__init__(parent or table.parent())

        # Don’t block clicks/scroll on the table underneath
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        # No own background — we only paint the green lines + corner sprites
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WA_StyledBackground, False)

        self.table = table

        # Load the four corner PNGs from the Qt resource system.
        # If you have @2x versions the device pixel ratio will be picked up automatically.
        self.pix_tl = QPixmap(":/ui/pixel_grid_corner_tl.png")
        self.pix_tr = QPixmap(":/ui/pixel_grid_corner_tr.png")
        self.pix_bl = QPixmap(":/ui/pixel_grid_corner_bl.png")
        self.pix_br = QPixmap(":/ui/pixel_grid_corner_br.png")

        # Start following geometry/layout events so we always hug the table.
        self._follower = _FollowEvents(table, self)
        self._sync_to_target()
        self.show()
        self.raise_()   # keep above the table


    # ----- Geometry sync -----------------------------------------------------

    def _sync_to_target(self) -> None:
        """
        Position and size the overlay to exactly match the table's rectangle
        (including its headers). We map the table's local (0,0) to the overlay
        parent’s coordinate system and set our geometry to that size/pos.
        """
        if not self.table or not self.table.isVisible():
            self.hide()
            return
        
        parent = self.parentWidget()
        if not parent:
            return
        
        # Convert table-local top-left into the parent coordinates we live in.
        top_left = self.table.mapTo(parent, QPoint(0, 0))
        size = self.table.size()

        # Snap our widget to that rect, then make sure we’re visible and repainted.
        self.setGeometry(QRect(top_left, size))
        self.show()
        self.raise_()
        self.update()

    # ----- Painting ----------------------------------------------------------

    def paintEvent(self, _) -> None:
        """
        Draw the outer 4px grid-color border (skipping under the corners) and
        then stamp the four pixel-corner sprites on top. The skip ensures the
        straight border lines don’t run under/through the curved pixels.
        """
        if not self.isVisible():
            return

        p = QPainter(self)

        #crisp, 4px #cfe8cf border ===
        GREEN = QColor("#cfe8cf")
        PEN_W = 4

        # No antialiasing so corners/lines remain perfectly sharp/pixelated
        p.setRenderHint(QPainter.Antialiasing, False)  # keep pixels crisp
        p.setPen(QPen(GREEN, PEN_W))

        r = self.rect()

        # Determine how much straight line to skip to make room for each corner sprite
        cw_tl = self.pix_tl.width()  if not self.pix_tl.isNull() else 0
        ch_tl = self.pix_tl.height() if not self.pix_tl.isNull() else 0
        cw_tr = self.pix_tr.width()  if not self.pix_tr.isNull() else 0
        ch_tr = self.pix_tr.height() if not self.pix_tr.isNull() else 0
        cw_bl = self.pix_bl.width()  if not self.pix_bl.isNull() else 0
        ch_bl = self.pix_bl.height() if not self.pix_bl.isNull() else 0
        cw_br = self.pix_br.width()  if not self.pix_br.isNull() else 0
        ch_br = self.pix_br.height() if not self.pix_br.isNull() else 0

        # Straight segments (leave gaps exactly where the corner sprites will sit)
        p.drawLine(r.left() + cw_tl, r.top(), r.right() - cw_tr, r.top())       # top
        p.drawLine(r.left() + cw_bl, r.bottom(), r.right() - cw_br, r.bottom()) # bottom
        p.drawLine(r.left(), r.top() + ch_tl, r.left(), r.bottom() - ch_bl)     # left
        p.drawLine(r.right(), r.top() + ch_tr, r.right(), r.bottom() - ch_br)   # right

        # Stamp the pixel corners over the ends of the straight segments
        if not self.pix_tl.isNull():
            p.drawPixmap(r.left(), r.top(), self.pix_tl)
        if not self.pix_tr.isNull():
            p.drawPixmap(r.right() - self.pix_tr.width() + 1, r.top(), self.pix_tr)
        if not self.pix_bl.isNull():
            p.drawPixmap(r.left(), r.bottom() - self.pix_bl.height() + 1, self.pix_bl)
        if not self.pix_br.isNull():
            p.drawPixmap(
                r.right() - self.pix_br.width() + 1,
                r.bottom() - self.pix_br.height() + 1,
                self.pix_br,
            )

        p.end()
