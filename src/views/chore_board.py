"""
chore_board.py — Scrollable list of ChoreCard widgets.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.db.repo.chores import list_chores
from src.db.session import SessionLocal
from src.services.dates import humanize_due
from src.views.chore_card import ChoreCard
from src.views.complete_chore_dialog import CompleteChoreDialog


def _assignee_label(chore) -> str:
    return chore.next_assignee.name if getattr(chore, "next_assignee", None) else "Unassigned"

class ChoreBoard(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        self.area = QScrollArea(self)
        self.area.setWidgetResizable(True)
        self.area.setFrameShape(QFrame.NoFrame)
        self.area.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        root.addWidget(self.area)

        # Content holds a grid – two columns, fixed-width cards
        self.content = QFrame()
        self.content.setFrameShape(QFrame.NoFrame)
        self.content.setStyleSheet("QFrame { border: none; background: transparent; }")
        self.grid = QGridLayout(self.content)
        self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(12)
        self.grid.setVerticalSpacing(12)

        # Equal width columns stretch to fill the row
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)

        # Don’t stretch columns — cards keep their fixed width
        self.area.setWidget(self.content)
        self.refresh()

    def _clear_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

    def refresh(self):
        self._clear_grid()

        with SessionLocal() as s:
            chores = list_chores(s)

        for i, ch in enumerate(chores):
            r = i // 2
            c = i % 2
            due_text = humanize_due(ch.next_due_date)
            card = ChoreCard(ch.id, ch.name, due_text, _assignee_label(ch))

            # Hook up actions
            card.completeClicked.connect(self._on_complete)

            # Let the card fill its cell (no alignment flags)
            self.grid.addWidget(card, r, c)

    # ----- Slots -----

    def _on_complete(self, chore_id: str):
        dlg = CompleteChoreDialog(chore_id, self)
        if dlg.exec():
            # after completion, refresh board
            self.refresh()
