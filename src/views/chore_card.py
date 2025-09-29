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
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

# Uniform height so cards in the same row align neatly.
CARD_H = 200   # uniform height for all cards

class ChoreCard(QWidget):
    """UI card for a single chore with title, meta, and actions."""

    # Signals carry the chore's id so the parent view can act on it.
    completeClicked = Signal(str)
    editClicked = Signal(str)

    def __init__(
        self,
        chore_id: str,
        name: str,
        description: str,
        due_text: str,
        assignee_text: str,
        parent=None
    ):
        """
        Build the card UI.

        Args:
            chore_id: Identifier for the chore (propagated via signals).
            name: Title of the chore.
            description: Description of the chore.
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
        v.setSpacing(0)  # no default gaps between rows

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

        self._desc_label = QLabel((description or "").strip())
        self._desc_label.setWordWrap(True)
        self._desc_label.setMargin(0)
        self._desc_label.setContentsMargins(0, 0, 0, 0)
        self._desc_label.setIndent(0)
        self._desc_label.setProperty("choreDesc", True)
        self._desc_label.setVisible(bool(self._desc_label.text()))
        hdr.addWidget(self._desc_label)

        v.addLayout(hdr)

        # Small gap before meta line
        v.addSpacing(6)

        # Meta line: due + next assignee
        self._meta_label = QLabel(f"Due: {due_text}  •  Next: {assignee_text}")
        self._meta_label.setProperty("choreMeta", True)
        self._meta_label.setContentsMargins(0, 0, 0, 0)
        v.addWidget(self._meta_label)

        # Actions row: Complete / Edit
        row = QHBoxLayout()

        btn_complete = QPushButton("Complete…")
        btn_edit     = QPushButton("Edit…")

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
        self._meta_label.setText(f"Due: {due_text}  •  Next: {assignee_text}")