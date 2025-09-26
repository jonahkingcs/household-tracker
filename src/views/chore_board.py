"""
chore_board.py — Scrollable grid of ChoreCard widgets with a fixed footer.

Overview
--------
- Displays chores as rounded "cards" in a 2-column grid inside a QScrollArea.
- Each card shows name, due info, assignee, and has Complete/Edit actions.
- A non-scrolling footer at the bottom-left provides an "Add Chore" button.

Data flow
---------
- Chores are read via repo.list_chores(SessionLocal()).
- Completing/editing/adding opens dialogs; on accept, the grid is refreshed.
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

from src.db.repo.chores import list_chores
from src.db.session import SessionLocal
from src.services.dates import humanize_due
from src.views.add_chore_dialog import AddChoreDialog
from src.views.chore_card import ChoreCard
from src.views.complete_chore_dialog import CompleteChoreDialog
from src.views.edit_chore_dialog import EditChoreDialog


def _assignee_label(chore) -> str:
    """Return the next assignee's display name or 'Unassigned' if missing."""
    return chore.next_assignee.name if getattr(chore, "next_assignee", None) else "Unassigned"

class ChoreBoard(QWidget):
    """Chores board widget.

    Structure:
        [ QScrollArea (fills available space)
            -> QFrame content
                -> QGridLayout (2 columns of ChoreCard widgets)
        ]
        [ Footer (non-scrolling): "Add Chore" button left-aligned ]

    Notes:
    - Columns are set to equal stretch so two cards fill the row and meet in the middle.
    - Cards have fixed height (handled by ChoreCard) but expand horizontally to share the row.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        # Root layout for the board
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        # --- Scroll area: holds the grid of chore cards; no outer border/background
        self.area = QScrollArea(self)
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.NoFrame)
        self.area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        root.addWidget(self.area)   # stretch by default; footer comes after

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

        # Don’t stretch columns so cards keep their fixed width
        self.area.setWidget(self.content)

        # --- Footer (fixed, non-scrolling): Add Chore button at bottom-left
        footer = QHBoxLayout()
        self.btn_add = QPushButton("Add Chore")
        self.btn_add.clicked.connect(self._on_add_chore)
        footer.addWidget(self.btn_add)  # pinned to the left
        footer.addStretch(1)            # push any future widgets to the left
        root.addLayout(footer)

        # Initial population of grid
        self.refresh()

    def _clear_grid(self):
        """Remove all widgets/items from the grid layout."""
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                # Detach widget from layout; Qt will delete later
                w.setParent(None)

    def refresh(self):
        """Rebuild the grid from the current chores in the database."""
        self._clear_grid()

        # Query chores once; SessionLocal context ensures proper closing
        with SessionLocal() as s:
            chores = list_chores(s)

        # Lay out cards two per row
        for i, ch in enumerate(chores):
            r = i // 2
            c = i % 2
            due_text = humanize_due(ch.next_due_date)

            # Build a card for this chore
            card = ChoreCard(
                ch.id,
                ch.name,
                ch.description or "",
                due_text,
                _assignee_label(ch)
                )

            # Hook up actions so the board can respond
            card.completeClicked.connect(self._on_complete)
            card.editClicked.connect(self._on_edit)

            # Let the card fill its cell; equal column stretch makes them meet in the middle
            self.grid.addWidget(card, r, c)

    # ----- Slots (UI actions) -----

    def _on_complete(self, chore_id: str):
        """Open the 'Complete Chore' dialog; on success, refresh the board."""
        dlg = CompleteChoreDialog(chore_id, self)
        if dlg.exec():
            # after completion, refresh board
            self.refresh()

    def _on_edit(self, chore_id: str):
        """Open the 'Edit Chore' dialog; on success, refresh the board."""
        dlg = EditChoreDialog(chore_id, self)
        if dlg.exec():
            self.refresh()

    def _on_add_chore(self):
        """Open the 'Add Chore' dialog; on success, refresh the board."""
        dlg = AddChoreDialog(self)
        if dlg.exec():
            self.refresh()
