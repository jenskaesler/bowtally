# -*- coding: utf-8 -*-
"""Pill showing a tournament status; colors come from the theme QSS (QLabel#statusBadge)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QSizePolicy

from bowtally.services.tournament_service import STATUS_LABELS


class StatusBadge(QLabel):
    def __init__(self, status: str = "draft", parent=None):
        super().__init__(parent)
        self.setObjectName("statusBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.set_status(status)

    def set_status(self, status: str) -> None:
        self.setText(f"●  {STATUS_LABELS.get(status, status)}")
        self.setProperty("status", status)
        # dynamic property changed -> re-evaluate the stylesheet
        self.style().unpolish(self)
        self.style().polish(self)
