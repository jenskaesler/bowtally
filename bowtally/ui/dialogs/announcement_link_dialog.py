# -*- coding: utf-8 -*-
"""Dialog for a link to an already published announcement, with a live QR preview."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QComboBox, QDialog, QLabel, QLineEdit, QVBoxLayout

from bowtally import config
from bowtally.services import announcement_link_service as als
from bowtally.ui import show_error, theme
from bowtally.ui.dialogs.record_dialog import RecordDialog
from bowtally.ui.utils.qr import qr_image

PREVIEW_PX = 180
_ICONS = {"website": "link", "facebook": "facebook", "instagram": "instagram",
          als.CUSTOM: "globe"}
_ASSET_ICONS = {"mein_bogenturnier": config.ASSETS_DIR / "platforms" / "mein_bogenturnier.png"}


def platform_pixmap(platform: str, size: int = 20) -> QPixmap:
    """Bundled platform icon (offline); unknown platforms get the globe."""
    if platform in _ASSET_ICONS:
        pix = QPixmap(str(_ASSET_ICONS[platform]))
        if not pix.isNull():
            return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                              Qt.TransformationMode.SmoothTransformation)
    return theme.pixmap(_ICONS.get(platform, "globe"), theme.current()["text2"], size)


def qr_pixmap(url: str, size: int) -> QPixmap:
    img = qr_image(url)
    if img.isNull():
        return QPixmap()
    return QPixmap.fromImage(img).scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                                         Qt.TransformationMode.FastTransformation)


class AnnouncementLinkDialog(RecordDialog):
    _default_size = (560, 0)

    def __init__(self, tournament_id: int, record=None, parent=None):
        self._record = record
        self._tournament_id = tournament_id
        super().__init__("Link hinzufügen" if record is None else "Link bearbeiten",
                         parent=parent)
        if record:
            self.form.set_values({"platform": record.platform,
                                  "platform_label": record.platform_label or "",
                                  "url": record.url})
        self._on_platform()
        self._update_preview()
        self._baseline = self.form.snapshot()
        self.saved_id: int | None = None

    def _setup_form(self):
        self._platform = QComboBox()
        for key, label in als.PLATFORMS.items():
            self._platform.addItem(platform_pixmap(key, 16), label, key)
        self._label = QLineEdit()
        self._label.setPlaceholderText("z. B. Vereinsnewsletter")
        self._url = QLineEdit()
        self._url.setPlaceholderText("https://…")
        self.form.add("platform", "Plattform", self._platform, required=True)
        self._label_field = self.form.add("platform_label", "Plattformname", self._label)
        self.form.add("url", "URL", self._url, required=True,
                      hint="Link zur bereits veröffentlichten Ausschreibung")
        self._preview = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        self._preview.setFixedSize(PREVIEW_PX, PREVIEW_PX)
        self._body_layout.addWidget(self._preview, 0, Qt.AlignmentFlag.AlignHCenter)
        self._platform.currentIndexChanged.connect(self._on_platform)
        self._url.textChanged.connect(self._update_preview)

    def _on_platform(self, *_):
        self._label_field.setVisible(self._platform.currentData() == als.CUSTOM)

    def _update_preview(self, *_):
        url = self._url.text().strip()
        if url:
            self._preview.setPixmap(qr_pixmap(url, PREVIEW_PX))
        else:
            self._preview.setPixmap(QPixmap())
            self._preview.setText("QR-Vorschau")

    def _do_save(self) -> bool:
        try:
            link = als.save_link(self.form.values(), self._record.id if self._record else None,
                                 self._tournament_id)
        except Exception as exc:
            show_error(self, exc, "Link konnte nicht gespeichert werden")
            return False
        self.saved_id = link.id
        return True


class QrZoomDialog(QDialog):
    """Enlarged QR code for a screenshot; no export, screen only."""

    def __init__(self, title: str, url: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"QR-Code: {title}")
        lay = QVBoxLayout(self)
        img = QLabel(alignment=Qt.AlignmentFlag.AlignCenter)
        img.setPixmap(qr_pixmap(url, 360))
        lay.addWidget(img)
        caption = QLabel(url, alignment=Qt.AlignmentFlag.AlignCenter, objectName="pageSubtitle")
        caption.setWordWrap(True)
        caption.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(caption)
