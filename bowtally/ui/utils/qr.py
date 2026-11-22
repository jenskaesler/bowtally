# -*- coding: utf-8 -*-
"""QR codes for the screen, offline: uses the QR encoder bundled with reportlab."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter


def qr_image(text: str, module_px: int = 6, border: int = 4) -> QImage:
    """Black-on-white QR code of `text`; a null QImage for empty text."""
    if not text:
        return QImage()
    from reportlab.graphics.barcode.qr import QrCodeWidget
    widget = QrCodeWidget(text)
    widget.qr.make()
    modules = widget.qr.modules
    size = (len(modules) + 2 * border) * module_px
    img = QImage(size, size, QImage.Format.Format_RGB32)
    img.fill(Qt.GlobalColor.white)
    p = QPainter(img)
    for r, row in enumerate(modules):
        for c, dark in enumerate(row):
            if dark:
                p.fillRect((c + border) * module_px, (r + border) * module_px,
                           module_px, module_px, Qt.GlobalColor.black)
    p.end()
    return img
