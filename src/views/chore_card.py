"""
chore_card.py — A compact, rounded "card" for a single chore.

Overview
--------
- Visual card used on the ChoreBoard grid (2 per row).
- Shows: title, due info (humanized), next assignee, and actions.
- Actions: "Complete…" and "Edit…" emit signals back to the board.

Styling
-------
- The widget uses objectName 'ChoreCard' so QSS can style the rounded border
  and tinted background (see styles/rounded_*.qss).
- Height is fixed (CARD_H) to keep rows visually aligned; width expands
  to share the row evenly with the second card.

Signals
-------
- completeClicked(chore_id: str): emitted when the Complete button is pressed.
- editClicked(chore_id: str):     emitted when the Edit button is pressed.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from src.ui.widgets.fade_button import FadeButton

# Uniform height so cards in the same row align neatly.
CARD_H = 200   # uniform height for all cards

class ChoreCard(QWidget):
    """UI card for a single chore with title, meta, and actions."""

    # Signals carry the chore's id so the parent view can act on it.
    completeClicked = Signal(str)
    editClicked = Signal(str)

    def __init__(self, chore_id: str, name: str, due_text: str, assignee_text: str, parent=None):
        """
        Build the card UI.

        Args:
            chore_id: Identifier for the chore (propagated via signals).
            name: Title of the chore.
            due_text: Humanized due info (e.g., "Today", "in 2d").
            assignee_text: Display name of the next assignee.
            parent: Optional Qt parent.
        """
        super().__init__(parent)
        self.chore_id = chore_id

        # Enable stylesheet-based rounded/tinted background.
        self.setObjectName("ChoreCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Fixed height across cards; width expands within the grid cell.
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(CARD_H)

        # ---- Layout scaffolding ----
        v = QVBoxLayout(self)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        # Title
        title = QLabel(name)
        title.setStyleSheet("font-weight: 600; font-size: 14pt;")   # or via QSS if you prefer
        v.addWidget(title)

        # Meta line: due + next assignee
        meta = QLabel(f"Due: {due_text}  •  Next: {assignee_text}")
        meta.setProperty("choreMeta", True)  # picked up by QSS for subtle color/size
        v.addWidget(meta)

        # Actions row: Complete / Edit
        row = QHBoxLayout()
        btn_complete = FadeButton("Complete…", hover_color="#f5dcf4", hover_alpha=90)
        btn_edit     = FadeButton("Edit…", hover_color="#f5dcf4", hover_alpha=90)
        row.addWidget(btn_complete)
        row.addStretch(1)   # push Edit to the far right
        row.addWidget(btn_edit)
        v.addLayout(row)

        # Wire actions to signals, carrying the chore id.
        btn_complete.clicked.connect(lambda: self.completeClicked.emit(self.chore_id))
        btn_edit.clicked.connect(lambda: self.editClicked.emit(self.chore_id))

    def update_meta(self, *, due_text: str, assignee_text: str):
        """
        Refresh the meta line (due and next assignee) without rebuilding the card.

        Args:
            due_text: Updated humanized due info.
            assignee_text: Updated next-assignee display name.
        """
        # Children order: 0 = title, 1 = meta label, 2 = button row.
        meta: QLabel = self.layout().itemAt(1).widget() # type: ignore[assignment]
        meta.setText(f"Due: {due_text}  •  Next: {assignee_text}")