"""
chore_card.py — A small card widget for a single chore.
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

CARD_H = 200   # uniform height for all cards

class ChoreCard(QWidget):
    # Signals carry the chore_id
    completeClicked = Signal(str)
    editClicked = Signal(str)

    def __init__(self, chore_id: str, name: str, due_text: str, assignee_text: str, parent=None):
        super().__init__(parent)
        self.chore_id = chore_id

        # Tie into QSS
        self.setObjectName("ChoreCard")
        self.setAttribute(Qt.WA_StyledBackground, True)

        # Fixed card size / policy
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(CARD_H)

        v = QVBoxLayout(self)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        title = QLabel(name)
        title.setStyleSheet("font-weight: 600; font-size: 14pt;")   # or via QSS if you prefer
        v.addWidget(title)

        meta = QLabel(f"Due: {due_text}  •  Next: {assignee_text}")
        meta.setProperty("choreMeta", True)  # QSS selector
        v.addWidget(meta)

        row = QHBoxLayout()
        btn_complete = QPushButton("Complete…")
        btn_edit = QPushButton("Edit…")
        row.addWidget(btn_complete)
        row.addStretch(1)
        row.addWidget(btn_edit)
        v.addLayout(row)

        btn_complete.clicked.connect(lambda: self.completeClicked.emit(self.chore_id))
        btn_edit.clicked.connect(lambda: self.editClicked.emit(self.chore_id))

    def update_meta(self, *, due_text: str, assignee_text: str):
        # 0:title, 1:meta, 2:row
        meta: QLabel = self.layout().itemAt(1).widget()
        meta.setText(f"Due: {due_text}  •  Next: {assignee_text}")