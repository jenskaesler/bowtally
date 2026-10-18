# -*- coding: utf-8 -*-
from PySide6.QtWidgets import QLabel


def page_title(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("pageTitle")
    return label
