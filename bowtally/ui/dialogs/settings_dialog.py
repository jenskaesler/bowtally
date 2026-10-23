# -*- coding: utf-8 -*-
"""Settings dialog: club profile, design (colors), print and behavior."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
                               QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QPlainTextEdit, QPushButton, QScrollArea, QSpinBox,
                               QTabWidget, QVBoxLayout, QWidget)

from bowtally.services import ValidationError, settings_service as ss
from bowtally.ui import button, show_error

LABEL_W = 130

CATEGORY_LABELS = {"ui": "Oberfläche", "print": "Druck", "behavior": "Verhalten",
                   "templates": "Textvorlagen (Ausschreibung)"}
HIDDEN_CATEGORIES = {"internal"}
MULTILINE_CATEGORIES = {"templates"}
CLUB_LABELS = {
    "club_name": "Vereinsname", "federation": "Verband", "club_number": "Verbandsnummer",
    "street": "Straße", "zip_code": "PLZ", "city": "Ort", "country": "Land",
    "phone": "Telefon", "email": "E-Mail", "website": "Webseite",
}
BANK_LABELS = {
    "bank_account_holder": "Kontoinhaber",
    "bank_iban": "IBAN",
    "bank_bic": "BIC",
    "bank_reference_template": "Verwendungszweck",
}
CONTACT_ROLES = {
    "first_board": "1. Vorsitzender/in",
    "second_board": "2. Vorsitzender/in",
    "treasurer": "Kassenwart/-in",
    "sports_dir": "Sportleiter/in",
    "bow_ref": "Bogenreferent/in",
}
COMBO_LABELS = {
    ss.KEY_PRINT_ORIENTATION: {"portrait": "Hochformat", "landscape": "Querformat"},
    ss.KEY_UI_LANGUAGE: {"de": "Deutsch"},
}
LABEL_OVERRIDES = {
    ss.KEY_PRINT_SHOW_LOGO: "Vereinslogo einfügen",
    ss.KEY_PRINT_SHOW_SCORES_PER_TARGET: "Einzelwertung einfügen",
    ss.KEY_UI_LANGUAGE: "Sprache",
    ss.KEY_FONT_FAMILY: "Schriftart",
    ss.KEY_RESULT_TIEBREAK_MODE: "Tie-Break-Logik",
    ss.KEY_RESULT_AUTO_RANK: "automatisch neu berechnen",
    ss.KEY_PRINT_PAPER_SIZE: "Papiergröße",
    ss.KEY_PRINT_ORIENTATION: "Format",
}
HIDDEN_KEYS = {"print_announcement_logo_footer"}
LOGO_PREVIEW = 120
COLOR_ORDER = ["_background", "_surface", "_border", "_text", "_text_secondary"]
BRAND_COLORS = {ss.KEY_COLOR_PRIMARY, ss.KEY_COLOR_SECONDARY, ss.KEY_COLOR_ACCENT}


def _valid_hex(text: str) -> bool:
    return text.startswith("#") and len(text) == 7 and QColor(text).isValid()


class ColorField(QWidget):
    def __init__(self, value: str, parent=None):
        super().__init__(parent)
        self.edit = QLineEdit(value)
        self.edit.setMaxLength(7)
        self.edit.setFixedWidth(100)
        self.swatch = QPushButton()
        self.swatch.setFixedSize(44, 32)
        self.swatch.setToolTip("Farbe auswählen")
        self.swatch.clicked.connect(self._pick)
        self.edit.textChanged.connect(self._update_swatch)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.edit)
        lay.addWidget(self.swatch)
        lay.addStretch()
        self._update_swatch(value)

    def _update_swatch(self, text: str):
        if _valid_hex(text):
            self.swatch.setStyleSheet(f"background: {text}; border: 1px solid #8889; "
                                      "border-radius: 6px;")

    def _pick(self):
        color = QColorDialog.getColor(QColor(self.value()), self, "Farbe wählen")
        if color.isValid():
            self.edit.setText(color.name().upper())

    def value(self) -> str:
        return self.edit.text().strip()

    def set_value(self, value: str):
        self.edit.setText(value)


class SettingsDialog(QDialog):
    def __init__(self, apply_theme, parent=None):
        """apply_theme(colors: dict | None) applies a (preview) theme to the app."""
        super().__init__(parent)
        self.apply_theme = apply_theme
        self.setWindowTitle("Einstellungen")
        self.resize(860, 720)
        self.settings = ss.all_settings()
        self.club_edits: dict = {}
        self.value_widgets: dict = {}

        tabs = QTabWidget()
        tabs.addTab(self._club_tab(), "Vereinsprofil")
        tabs.addTab(self._contacts_tab(), "Vereinsvorstand")
        tabs.addTab(self._bank_tab(), "Bankdaten")
        tabs.addTab(self._design_tab(), "Design")
        tabs.addTab(self._category_tab("behavior", "ui"), "Verhalten")
        tabs.addTab(self._print_tab(), "Druck")
        tabs.addTab(self._backup_tab(), "Backup")

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Speichern")
        buttons.button(QDialogButtonBox.StandardButton.Save).setProperty("primary", True)
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Abbrechen")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        lay = QVBoxLayout(self)
        lay.addWidget(tabs)
        lay.addWidget(buttons)

    @staticmethod
    def _flbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setMinimumWidth(LABEL_W)
        return lbl

    # ------------------------------------------------------------ tab 1
    def _club_tab(self) -> QWidget:
        club = ss.get_club_profile()
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setSpacing(10)

        for box_title, keys in (
            ("Verein", ("club_name", "federation", "club_number")),
            ("Adresse", ("street", "zip_code", "city", "country")),
            ("Kontakt", ("phone", "email", "website")),
        ):
            box = QGroupBox(box_title)
            form = QFormLayout(box)
            for key in keys:
                edit = QLineEdit(club.get(key) or "")
                self.club_edits[key] = edit
                form.addRow(self._flbl(CLUB_LABELS[key]), edit)
            lay.addWidget(box)

        box_default_contact = QGroupBox("Standard-Kontaktperson")
        form_dc = QFormLayout(box_default_contact)
        self._default_contact_combo = QComboBox()
        for role_key, role_label in CONTACT_ROLES.items():
            self._default_contact_combo.addItem(role_label, role_key)
        stored_role = ss.get("default_contact_role", "treasurer")
        idx = self._default_contact_combo.findData(stored_role)
        if idx >= 0:
            self._default_contact_combo.setCurrentIndex(idx)
        self.value_widgets["default_contact_role"] = self._default_contact_combo
        form_dc.addRow(self._flbl("Rolle"), self._default_contact_combo)
        lay.addWidget(box_default_contact)

        box_notes = QGroupBox("Notizen")
        QVBoxLayout(box_notes)
        edit_notes = QPlainTextEdit(club.get("notes") or "")
        edit_notes.setMinimumHeight(120)
        self.club_edits["notes"] = edit_notes
        box_notes.layout().addWidget(edit_notes)
        lay.addWidget(box_notes)

        box_logo = QGroupBox("Logo")
        logo_lay = QHBoxLayout(box_logo)
        self.logo_edit = QLineEdit(club.get("logo_path") or "")
        self.logo_edit.textChanged.connect(self._update_logo)
        self.logo_preview = QLabel()
        self.logo_preview.setFixedSize(LOGO_PREVIEW, LOGO_PREVIEW)
        self.logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_preview.setFrameShape(QLabel.Shape.StyledPanel)
        col = QVBoxLayout()
        col.addWidget(self.logo_edit)
        row_btns = QHBoxLayout()
        row_btns.addWidget(button("Durchsuchen ...", self._browse_logo))
        row_btns.addWidget(button("Entfernen", lambda: self.logo_edit.clear()))
        row_btns.addStretch()
        col.addLayout(row_btns)
        col.addStretch()
        logo_lay.addLayout(col, 1)
        logo_lay.addWidget(self.logo_preview)
        self._update_logo(self.logo_edit.text())
        lay.addWidget(box_logo)
        lay.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        return scroll

    def _contacts_tab(self) -> QWidget:
        club = ss.get_club_profile()
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setSpacing(10)
        for role_key, role_label in CONTACT_ROLES.items():
            box = QGroupBox(role_label)
            form = QFormLayout(box)
            for field, placeholder, label in (
                (f"{role_key}_fname", "Vorname", "Vorname"),
                (f"{role_key}_lname", "Nachname", "Nachname"),
                (f"{role_key}_phone", "Telefonnummer", "Telefon"),
                (f"{role_key}_email", "E-Mail-Adresse", "E-Mail"),
            ):
                edit = QLineEdit(club.get(field) or "")
                edit.setPlaceholderText(placeholder)
                self.club_edits[field] = edit
                form.addRow(self._flbl(label), edit)
            lay.addWidget(box)
        lay.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        return scroll

    def _browse_logo(self):
        path, _ = QFileDialog.getOpenFileName(self, "Logo auswählen", "",
                                              "Bilder (*.png *.jpg *.jpeg)")
        if path:
            self.logo_edit.setText(path)

    def _update_logo(self, path: str):
        pix = QPixmap(path) if path else QPixmap()
        if pix.isNull():
            self.logo_preview.setText("Kein Logo" if not path else "Datei nicht lesbar")
            self.logo_preview.setPixmap(QPixmap())
        else:
            self.logo_preview.setPixmap(pix.scaled(LOGO_PREVIEW - 8, LOGO_PREVIEW - 8,
                                                   Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation))

    # ------------------------------------------------------------ tab 2
    def _design_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        values = {st.key: st.value for st in self.settings}
        self.mode = QComboBox()
        for key, label in ss.THEME_MODE_LABELS.items():
            self.mode.addItem(label, key)
        self.mode.setCurrentIndex(max(0, self.mode.findData(
            values.get(ss.KEY_UI_THEME_MODE) or "system")))
        self.mode.currentIndexChanged.connect(self._preview)
        mode_row = QFormLayout()
        mode_row.addRow(self._flbl("Darstellung"), self.mode)
        lay.addLayout(mode_row)

        self.color_fields: dict[str, ColorField] = {}
        boxes = {"brand": QFormLayout(), "light": QFormLayout(), "dark": QFormLayout()}
        colors = sorted((st for st in self.settings if st.value_type == "color"),
                        key=lambda st: next((i for i, suffix in enumerate(COLOR_ORDER)
                                             if st.key.endswith(suffix)), len(COLOR_ORDER)))
        for st in colors:
            field = ColorField(st.value or ss.DEFAULTS.get(st.key, "#000000"))
            self.color_fields[st.key] = field
            group = ("brand" if st.key in BRAND_COLORS else
                     "dark" if st.key.startswith("color_dark_") else "light")
            boxes[group].addRow((st.description or st.key).replace(" (Dunkel)", ""), field)
        cols = QHBoxLayout()
        brand_box = QGroupBox("Markenfarben (beide Modi)")
        brand_box.setLayout(boxes["brand"])
        lay.addWidget(brand_box)
        for group, title in (("light", "Hell"), ("dark", "Dunkel")):
            box = QGroupBox(title)
            box.setLayout(boxes[group])
            cols.addWidget(box)
        lay.addLayout(cols)
        btns = QHBoxLayout()
        btns.addWidget(button("Vorschau anwenden", self._preview, "primary"))
        btns.addWidget(button("Zurücksetzen auf Standard", self._reset_colors))
        btns.addStretch()
        lay.addLayout(btns)
        lay.addStretch()
        return w

    def _colors(self) -> dict[str, str]:
        bad = [k for k, f in self.color_fields.items() if not _valid_hex(f.value())]
        if bad:
            raise ValidationError("Ungültiger Farbwert (Format #RRGGBB): " + ", ".join(bad))
        values = {k: f.value() for k, f in self.color_fields.items()}
        values[ss.KEY_UI_THEME_MODE] = self.mode.currentData()
        return values

    def _preview(self):
        try:
            self.apply_theme(self._colors())
        except ValidationError as exc:
            show_error(self, exc)

    def _reset_colors(self):
        defaults = ss.color_defaults()
        for key, field in self.color_fields.items():
            if key in defaults:
                field.set_value(defaults[key])
        self._preview()

    # ------------------------------------------------------------ tab 2b (bank) / tabs 4+5
    def _bank_tab(self) -> QWidget:
        club = ss.get_club_profile()
        w = QWidget()
        lay = QVBoxLayout(w)
        box = QGroupBox("Bankverbindung")
        form = QFormLayout(box)
        for key, label in BANK_LABELS.items():
            edit = QLineEdit(club.get(key) or "")
            if key == "bank_iban":
                edit.setPlaceholderText("DE00 0000 0000 0000 0000 00")
            if key == "bank_reference_template":
                edit.setPlaceholderText("z. B. 3D Turnier 2027, {name}, {bow_class}")
            self.club_edits[key] = edit
            form.addRow(self._flbl(label), edit)
        hint = QLabel("Platzhalter Verwendungszweck: {name}, {bow_class}",
                      objectName="pageSubtitle")
        form.addRow("", hint)
        lay.addWidget(box)
        lay.addStretch()
        return w

    def _backup_tab(self) -> QWidget:
        from bowtally.services import backup_service as bs
        w = QWidget()
        lay = QVBoxLayout(w)

        auto_box = QGroupBox("Automatisches Backup")
        auto_lay = QVBoxLayout(auto_box)
        self._backup_on_close = QCheckBox("Backup beim Beenden der App erstellen")
        self._backup_on_close.setChecked(ss.get_bool("backup_on_close"))
        auto_lay.addWidget(self._backup_on_close)
        lay.addWidget(auto_box)

        local_box = QGroupBox("Lokales Backup (NAS / USB)")
        local_form = QFormLayout(local_box)
        self._backup_path_edit = QLineEdit(ss.get("backup_local_path") or "")
        self._backup_path_edit.setPlaceholderText("Pfad zum Backup-Ordner …")
        browse_btn = button("…", lambda: self._browse_backup_path())
        path_row = QHBoxLayout()
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.addWidget(self._backup_path_edit, 1)
        path_row.addWidget(browse_btn)
        path_widget = QWidget()
        path_widget.setLayout(path_row)
        self._backup_retention = QSpinBox()
        self._backup_retention.setRange(1, 99)
        self._backup_retention.setValue(int(ss.get("backup_retention", "10") or 10))
        self._backup_retention.setSuffix(" Backups behalten")
        local_form.addRow(self._flbl("Backup-Pfad"), path_widget)
        local_form.addRow(self._flbl("Aufbewahrung"), self._backup_retention)
        local_btns = QHBoxLayout()
        local_btns.addWidget(button("Backup jetzt erstellen", lambda: self._do_local_backup(bs),
                                    "primary", "Datenbank als ZIP in den Backup-Ordner sichern"))
        local_btns.addStretch()
        lay.addWidget(local_box)
        lay.addLayout(local_btns)

        nc_box = QGroupBox("Nextcloud")
        nc_form = QFormLayout(nc_box)
        self._nc_url = QLineEdit(ss.get("backup_nc_url") or "")
        self._nc_url.setPlaceholderText("https://nextcloud.example.com")
        self._nc_user = QLineEdit(ss.get("backup_nc_user") or "")
        self._nc_pass = QLineEdit(ss.get("backup_nc_pass") or "")
        self._nc_pass.setEchoMode(QLineEdit.EchoMode.Password)
        nc_form.addRow(self._flbl("URL"), self._nc_url)
        nc_form.addRow(self._flbl("Benutzername"), self._nc_user)
        nc_form.addRow(self._flbl("Passwort"), self._nc_pass)
        nc_btns = QHBoxLayout()
        nc_btns.addWidget(button("Zu Nextcloud sichern", lambda: self._do_nc_backup(bs),
                                 tooltip="Backup in Nextcloud hochladen"))
        nc_btns.addStretch()
        lay.addWidget(nc_box)
        lay.addLayout(nc_btns)

        restore_box = QGroupBox("Wiederherstellen")
        restore_lay = QVBoxLayout(restore_box)
        restore_lay.addWidget(QLabel("Wähle eine lokale Backup-Datei (.zip):",
                                     objectName="pageSubtitle"))
        restore_btns = QHBoxLayout()
        restore_btns.addWidget(button("Backup wiederherstellen",
                                      lambda: self._do_restore(bs),
                                      "danger",
                                      "Backup-ZIP auswählen und Datenbank ersetzen"))
        restore_btns.addStretch()
        restore_lay.addLayout(restore_btns)
        lay.addWidget(restore_box)
        lay.addStretch()
        return w

    def _browse_backup_path(self):
        path = QFileDialog.getExistingDirectory(self, "Backup-Ordner auswählen",
                                                self._backup_path_edit.text())
        if path:
            self._backup_path_edit.setText(path)

    def _save_backup_settings(self):
        ss.set_many({"backup_local_path": self._backup_path_edit.text().strip(),
                     "backup_retention": str(self._backup_retention.value()),
                     "backup_nc_url": self._nc_url.text().strip(),
                     "backup_nc_user": self._nc_user.text().strip(),
                     "backup_nc_pass": self._nc_pass.text().strip(),
                     "backup_on_close": "true" if self._backup_on_close.isChecked() else "false"})

    def _do_local_backup(self, bs):
        self._save_backup_settings()
        try:
            path = bs.backup_local()
        except Exception as exc:
            show_error(self, exc, "Backup fehlgeschlagen")
            return
        from bowtally.ui.components.toast import Toast
        Toast.show(self, f"Backup erstellt: {path}", Toast.SUCCESS)

    def _do_nc_backup(self, bs):
        self._save_backup_settings()
        try:
            bs.backup_nextcloud()
        except Exception as exc:
            show_error(self, exc, "Nextcloud-Backup fehlgeschlagen")
            return
        from bowtally.ui.components.toast import Toast
        Toast.show(self, "Backup zu Nextcloud hochgeladen", Toast.SUCCESS)

    def _do_restore(self, bs):
        path, _ = QFileDialog.getOpenFileName(self, "Backup auswählen", "",
                                               "ZIP-Dateien (*.zip)")
        if not path:
            return
        from bowtally.ui.components.confirm_dialog import ConfirmDialog
        if not ConfirmDialog.ask(self, "Datenbank wiederherstellen?",
                                 "Die aktuelle Datenbank wird durch das Backup ersetzt.\n"
                                 "Dieser Vorgang kann nicht rückgängig gemacht werden.",
                                 "Wiederherstellen", destructive=True):
            return
        try:
            bs.restore(path)
        except Exception as exc:
            show_error(self, exc, "Wiederherstellung fehlgeschlagen")
            return
        from bowtally.ui.components.toast import Toast
        Toast.show(self, "Backup wiederhergestellt – bitte Anwendung neu starten", Toast.SUCCESS)

    def _print_tab(self) -> QWidget:
        club = ss.get_club_profile()
        edit_course = QPlainTextEdit(club.get("course_description") or "")
        edit_course.setFixedHeight(90)
        edit_course.setPlaceholderText(
            "z. B. Waldparcours ca. 4 km, festes Schuhwerk erforderlich")
        self.club_edits["course_description"] = edit_course
        inner = QWidget()
        lay = QVBoxLayout(inner)
        groups: dict[str, QFormLayout] = {}
        for st in self.settings:
            if st.value_type == "color" or st.key == ss.KEY_UI_THEME_MODE \
                    or st.key in HIDDEN_KEYS \
                    or st.category not in ("print", "templates") \
                    or st.category in HIDDEN_CATEGORIES:
                continue
            if st.category not in groups:
                box = QGroupBox(CATEGORY_LABELS.get(st.category, st.category or "Allgemein"))
                groups[st.category] = QFormLayout(box)
                lay.addWidget(box)
                if st.category == "templates":
                    lbl = self._flbl("Parcours-Beschreibung")
                    lbl.setWordWrap(True)
                    groups["templates"].addRow(lbl, edit_course)
            widget = self._widget_for(st)
            self.value_widgets[st.key] = widget
            label = self._flbl(LABEL_OVERRIDES.get(st.key) or st.description or st.key)
            label.setWordWrap(True)
            label.setToolTip(st.key)
            groups[st.category].addRow(label, widget)
        lay.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        return scroll

    def _category_tab(self, *categories: str) -> QWidget:
        inner = QWidget()
        lay = QVBoxLayout(inner)
        groups: dict[str, QFormLayout] = {}
        for st in self.settings:
            if st.value_type == "color" or st.key == ss.KEY_UI_THEME_MODE \
                    or st.key in HIDDEN_KEYS \
                    or st.category not in categories or st.category in HIDDEN_CATEGORIES:
                continue
            if st.category not in groups:
                box = QGroupBox(CATEGORY_LABELS.get(st.category, st.category or "Allgemein"))
                groups[st.category] = QFormLayout(box)
                lay.addWidget(box)
            widget = self._widget_for(st)
            self.value_widgets[st.key] = widget
            label = self._flbl(LABEL_OVERRIDES.get(st.key) or st.description or st.key)
            label.setWordWrap(True)
            label.setToolTip(st.key)
            groups[st.category].addRow(label, widget)
        lay.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        return scroll

    def _widget_for(self, st):
        value = st.value or ""
        if st.value_type == "boolean":
            w = QCheckBox()
            w.setChecked(value.lower() in ("1", "true", "yes", "ja"))
        elif st.value_type == "integer":
            w = QSpinBox()
            w.setRange(-1_000_000, 1_000_000)
            w.setValue(int(value or 0))
        elif st.category in MULTILINE_CATEGORIES:
            w = QPlainTextEdit(value)
            w.setFixedHeight(90)
        elif st.key in ss.OPTIONS:
            w = QComboBox()
            display = COMBO_LABELS.get(st.key, {})
            for val in ss.OPTIONS[st.key]:
                w.addItem(display.get(val, val), val)
            idx = w.findData(value) if value else -1
            w.setCurrentIndex(idx if idx >= 0 else 0)
        elif st.value_type == "path":
            w = QWidget()
            w.edit = QLineEdit(value)
            row = QHBoxLayout(w)
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(w.edit)
            row.addWidget(button("...", lambda _=False, e=w.edit: self._browse_path(e)))
        else:
            w = QLineEdit(value)
        return w

    def _browse_path(self, edit: QLineEdit):
        path, _ = QFileDialog.getOpenFileName(self, "Datei auswählen", edit.text())
        if path:
            edit.setText(path)

    @staticmethod
    def _value_of(w) -> str:
        if isinstance(w, QCheckBox):
            return "true" if w.isChecked() else "false"
        if isinstance(w, QSpinBox):
            return str(w.value())
        if isinstance(w, QComboBox):
            data = w.currentData()
            return data if data is not None else w.currentText()
        if isinstance(w, QLineEdit):
            return w.text().strip()
        if isinstance(w, QPlainTextEdit):
            return w.toPlainText().strip()
        return w.edit.text().strip()

    # ------------------------------------------------------------ save
    def _save(self):
        try:
            values = self._colors()
            values.update({k: self._value_of(w) for k, w in self.value_widgets.items()})
            club = {k: (e.toPlainText() if isinstance(e, QPlainTextEdit) else e.text()).strip()
                    for k, e in self.club_edits.items()}
            club["logo_path"] = self.logo_edit.text().strip()
            ss.set_many(values)
            ss.save_club_profile(club)
        except Exception as exc:
            show_error(self, exc, "Einstellungen konnten nicht gespeichert werden")
            return
        self.accept()
