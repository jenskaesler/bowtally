# -*- coding: utf-8 -*-
"""Keeps a widget at half the height of its page (QFormLayout never grows its rows by itself)."""
from PySide6.QtCore import QEvent, QObject


def keep_half_height(page, widget) -> None:
    class _Filter(QObject):
        def eventFilter(self, _obj, event):
            if event.type() == QEvent.Type.Resize:
                widget.setMinimumHeight(page.height() // 2)
            return False

    page._half_height_filter = f = _Filter(page)
    page.installEventFilter(f)
