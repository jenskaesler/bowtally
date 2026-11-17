# -*- coding: utf-8 -*-
"""Settings dialog: club profile, design (colors), print, export path and behavior."""
from pathlib import Path
import json
from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QColorDialog, QComboBox, QDialog,
                               QFileDialog, QFormLayout, QFrame, QGridLayout,
                               QGroupBox, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
                               QListWidgetItem, QPlainTextEdit, QPushButton,
                               QScrollArea, QSizePolicy, QSpinBox, QStackedWidget, QToolButton,
                               QVBoxLayout, QWidget)

from bowtally import config
from bowtally.services import ValidationError, settings_service as ss
from bowtally.ui import burger_button, button, restore_geom, save_geom, show_error, theme

CATEGORY_LABELS = {"ui": "Oberfläche", "print": "Druck", "behavior": "Verhalten",
                   "templates": "Textvorlagen"}
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
    "waitlist_mode": {"block": "Gesperrt (kein Nachrücken)", "auto": "Automatisch (Warteliste)"},
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
    "announcement_payment_hint": "Überweisungshinweis",
    "announcement_group_hint": "Gruppenhinweis",
    "default_legal_notes": "Wichtige Hinweise",
    "waitlist_mode": "Warteliste bei Vollbelegung",
}
HIDDEN_KEYS = {"print_announcement_logo_footer"}
NAV_KEYS = ["dashboard", "tournaments", "calendar", "archers",
            "helpers", "rules", "bow_classes", "inventory", "logbuch"]
NAV_LABELS = {
    "dashboard": "Dashboard", "logbuch": "Logbuch",
    "calendar": "Kalender", "archers": "Schützen", "helpers": "Mitglieder",
    "rules": "Regelwerke", "bow_classes": "Bogenklassen", "inventory": "Inventar",
    "tournaments": "Turniere",
}
NAV_LOCKED = {"dashboard"}     # cannot be hidden
VISIBLE_ROLE = Qt.ItemDataRole.UserRole + 1
LOGO_PREVIEW = 120
SETTINGS_LABEL_W = 200   # fixed label column width so all tabs align
SETTINGS_COMBO_W = 220   # fixed width for combos / spinboxes / pickers
COLOR_ORDER = ["_background", "_surface", "_border", "_text", "_text_secondary"]
BRAND_COLORS = {ss.KEY_COLOR_PRIMARY, ss.KEY_COLOR_SECONDARY, ss.KEY_COLOR_ACCENT}


def _valid_hex(text: str) -> bool:
    return text.startswith("#") and len(text) == 7 and QColor(text).isValid()


def _browse_export_path(edit: QLineEdit, parent=None):
    path = QFileDialog.getExistingDirectory(parent, "Standard-Exportpfad wählen",
                                            edit.text() or str(Path.home() / "Downloads"))
    if path:
        edit.setText(path)


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


class _ResizeGrip(QFrame):
    def __init__(self, target):
        super().__init__()
        self._t = target
        self._y0 = self._h0 = 0
        self.setFixedHeight(6)
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Sunken)
        self.setCursor(Qt.CursorShape.SizeVerCursor)

    def mousePressEvent(self, e):
        self._y0 = int(e.globalPosition().y())
        self._h0 = self._t.height()

    def mouseMoveEvent(self, e):
        delta = int(e.globalPosition().y()) - self._y0
        self._t.setFixedHeight(max(60, self._h0 + delta))


def _with_grip(edit):
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)
    lay.addWidget(edit, 1)
    lay.addWidget(_ResizeGrip(w))
    w.setMinimumHeight(edit.minimumHeight() + 6)
    return w


class SettingsDialog(QDialog):
    _NAV_GROUPS = [
        ("VEREINSVERWALTUNG",  [("club", "Vereinsprofil"),
                                 ("contacts", "Vereinsvorstand"),
                                 ("bank", "Bankdaten")]),
        ("TURNIERVERWALTUNG",  [("behavior", "Allgemein"),
                                 ("print", "Druck & Listen"),
                                 ("email", "E-Mail-Vorlagen")]),
        ("SYSTEM",             [("general", "Allgemein"),
                                 ("backup", "Backup")]),
        ("DARSTELLUNG",        [("design", "Design"),
                                 ("ui", "Oberfläche"),
                                 ("nav", "Navigation")]),
    ]

    def __init__(self, apply_theme, parent=None):
        """apply_theme(colors: dict | None) applies a (preview) theme to the app."""
        super().__init__(parent)
        self.apply_theme = apply_theme
        self.setWindowTitle("Einstellungen")
        self.resize(900, 640)
        restore_geom(self, "settings")
        self.finished.connect(lambda: save_geom(self, "settings"))
        self.settings = ss.all_settings()
        self.club_edits: dict = {}
        self.value_widgets: dict = {}

        # Build all pages
        all_pages = [
            ("club",     self._club_tab()),
            ("contacts", self._contacts_tab()),
            ("bank",     self._bank_tab()),
            ("design",   self._design_tab()),
            ("ui",       self._category_tab("ui")),
            ("behavior", self._category_tab("behavior")),
            ("print",    self._print_tab()),
            ("email",    self._email_tab()),
            ("general",  self._general_tab()),
            ("backup",   self._backup_tab()),
            ("nav",      self._nav_tab()),
        ]
        self._stack = QStackedWidget()
        self._page_index: dict[str, int] = {}
        for key, widget in all_pages:
            self._page_index[key] = self._stack.count()
            self._stack.addWidget(widget)

        # Sidebar
        from bowtally.ui import theme as _th
        t = _th.current()
        sidebar = QWidget()
        sidebar.setFixedWidth(220)
        sidebar_lay = QVBoxLayout(sidebar)
        sidebar_lay.setContentsMargins(8, 8, 8, 8)
        sidebar_lay.setSpacing(6)

        self._settings_search = QLineEdit()
        self._settings_search.setPlaceholderText("Suchen …")
        self._settings_search.setClearButtonEnabled(True)
        sidebar_lay.addWidget(self._settings_search)

        self._settings_nav = QListWidget()
        self._settings_nav.setObjectName("settingsNav")
        self._settings_nav.setSpacing(1)
        self._results_list = QListWidget()
        self._results_list.setSpacing(2)
        self._nav_stack = QStackedWidget()
        self._nav_stack.addWidget(self._settings_nav)
        self._nav_stack.addWidget(self._results_list)
        sidebar_lay.addWidget(self._nav_stack, 1)

        header_font = QFont()
        header_font.setPointSize(8)
        header_font.setBold(True)
        self._nav_entries: list[tuple] = []  # (item, key_or_None)
        for group_title, items in self._NAV_GROUPS:
            hdr = QListWidgetItem(group_title)
            hdr.setFlags(Qt.ItemFlag.NoItemFlags)
            hdr.setFont(header_font)
            hdr.setForeground(QColor(t["text2"]))
            self._settings_nav.addItem(hdr)
            self._nav_entries.append((hdr, None))
            for key, label in items:
                item = QListWidgetItem("  " + label)
                item.setData(Qt.ItemDataRole.UserRole, key)
                self._settings_nav.addItem(item)
                self._nav_entries.append((item, key))

        self._settings_nav.currentItemChanged.connect(self._on_settings_nav)
        self._results_list.itemActivated.connect(self._on_settings_result)

        # Vertical separator
        vline = QFrame()
        vline.setFrameShape(QFrame.Shape.VLine)
        vline.setFrameShadow(QFrame.Shadow.Sunken)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(sidebar)
        body.addWidget(vline)
        body.addWidget(self._stack, 1)

        self._save_btn = button("Speichern", self._save_settings, "danger",
                                "Ungespeicherte Änderungen speichern")
        self._save_btn.setEnabled(False)
        close_btn = button("Schließen", self._close_dialog, "primary")
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_row.addWidget(self._save_btn)
        btn_row.addWidget(close_btn)

        lay = QVBoxLayout(self)
        lay.addLayout(body, 1)
        lay.addLayout(btn_row)

        self._search_index = self._build_search_index()
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(
            lambda: self._do_settings_search(self._settings_search.text()))
        self._settings_search.textChanged.connect(lambda: self._search_timer.start())
        self._select_settings_page("club")
        self._saved = self._state()
        self._connect_changes()

    def _on_settings_nav(self, current, _prev):
        if current is None:
            return
        key = current.data(Qt.ItemDataRole.UserRole)
        if key and key in self._page_index:
            self._stack.setCurrentIndex(self._page_index[key])

    def _build_search_index(self) -> list[dict]:
        index = []
        for _group_title, items in self._NAV_GROUPS:
            for nav_key, nav_label in items:
                if nav_key not in self._page_index:
                    continue
                page = self._stack.widget(self._page_index[nav_key])
                for group_box in page.findChildren(QGroupBox):
                    group_label = group_box.title()
                    for label in group_box.findChildren(QLabel):
                        text = label.text().strip()
                        if not text or text.startswith('<') or len(text) < 2:
                            continue
                        index.append({
                            'nav_key': nav_key, 'nav_label': nav_label,
                            'group_label': group_label, 'field_label': text,
                            'widget': label,
                            'searchable': f"{nav_label} {group_label} {text}".lower(),
                        })
                    for chk in group_box.findChildren(QCheckBox):
                        text = chk.text().strip()
                        if not text:
                            continue
                        index.append({
                            'nav_key': nav_key, 'nav_label': nav_label,
                            'group_label': group_label, 'field_label': text,
                            'widget': chk,
                            'searchable': f"{nav_label} {group_label} {text}".lower(),
                        })
        return index

    def _do_settings_search(self, text: str):
        text = text.strip()
        if len(text) < 2:
            for item, _ in self._nav_entries:
                item.setHidden(False)
            self._nav_stack.setCurrentWidget(self._settings_nav)
            return
        needle = text.lower()
        hits = [e for e in self._search_index if needle in e['searchable']]
        rl = self._results_list
        rl.clear()
        if not hits:
            item = QListWidgetItem("Keine Einstellungen gefunden")
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            rl.addItem(item)
        else:
            for e in hits:
                item = QListWidgetItem(
                    f"{e['nav_label']} › {e['group_label']}\n{e['field_label']}")
                item.setData(Qt.ItemDataRole.UserRole, e)
                item.setSizeHint(QSize(0, 44))
                rl.addItem(item)
        self._nav_stack.setCurrentWidget(rl)

    def _on_settings_result(self, item: QListWidgetItem):
        e = item.data(Qt.ItemDataRole.UserRole)
        if e is None:
            return
        self._select_settings_page(e['nav_key'])
        self._highlight_label(e['widget'])

    def _highlight_label(self, widget):
        orig = widget.styleSheet()
        widget.setStyleSheet("background-color: #FFF176; border-radius: 3px;")
        t = QTimer(self)
        t.setSingleShot(True)
        t.timeout.connect(lambda: widget.setStyleSheet(orig))
        t.start(2000)

    def _select_settings_page(self, key: str):
        for item, k in self._nav_entries:
            if k == key:
                self._settings_nav.setCurrentItem(item)
                return

    def _nav_order_json(self) -> str:
        return json.dumps([
            {"key": self._nav_list_widget.item(i).data(Qt.ItemDataRole.UserRole),
             "visible": bool(self._nav_list_widget.item(i).data(VISIBLE_ROLE))}
            for i in range(self._nav_list_widget.count())
        ])

    def _state(self) -> dict:
        """All editable values, as the settings would be saved."""
        try:
            values = self._colors()
        except ValidationError:
            values = {}
        values.update({k: self._value_of(w) for k, w in self.value_widgets.items()})
        club = {k: (e.toPlainText() if isinstance(e, QPlainTextEdit) else e.text()).strip()
                for k, e in self.club_edits.items()}
        club["logo_path"] = self._logo_path
        return {"values": values, "club": club, "nav": self._nav_order_json(),
                "backup": self._backup_values()}

    def _update_save_btn(self):
        self._save_btn.setEnabled(self._state() != self._saved)

    def _save_settings(self):
        try:
            state = self._state()
            # first: refuses an empty backup password before anything is saved (only if auto backup is on)
            self._save_backup_settings(password_required=self._backup_on_close.isChecked())
            ss.set_many(state["values"])
            ss.set_value("nav_order", state["nav"])
            ss.save_club_profile(state["club"])
        except Exception as exc:
            show_error(self, exc, "Einstellungen konnten nicht gespeichert werden")
            return
        self._saved = self._state()
        self._update_save_btn()

    def _close_dialog(self):
        if self._may_close():
            self.accept()

    def reject(self):
        if self._may_close():
            super().reject()

    def _may_close(self) -> bool:
        """True if nothing is unsaved or the user chose to discard the changes."""
        if self._state() == self._saved:
            return True
        from bowtally.ui.components.confirm_dialog import ConfirmDialog
        if ConfirmDialog.ask(self, "Ungespeicherte Änderungen",
                             "Es gibt ungespeicherte Änderungen. Verwerfen und schließen?\n"
                             "„Abbrechen“ führt zurück zu den Einstellungen.",
                             "Verwerfen", destructive=True):
            self.apply_theme()     # drop the live preview
            return True
        return False

    def _connect_changes(self):
        for w in self.value_widgets.values():
            if isinstance(w, QCheckBox):
                w.toggled.connect(self._update_save_btn)
            elif isinstance(w, QComboBox):
                w.currentIndexChanged.connect(self._update_save_btn)
            elif isinstance(w, QSpinBox):
                w.valueChanged.connect(self._update_save_btn)
            elif isinstance(w, QLineEdit):
                w.textChanged.connect(self._update_save_btn)
            elif isinstance(w, QPlainTextEdit):
                w.textChanged.connect(self._update_save_btn)
            elif hasattr(w, 'edit') and isinstance(w.edit, QLineEdit):
                w.edit.textChanged.connect(self._update_save_btn)
        for e in self.club_edits.values():
            e.textChanged.connect(self._update_save_btn)
        if hasattr(self, 'mode'):
            self.mode.currentIndexChanged.connect(self._update_save_btn)
        for f in getattr(self, 'color_fields', {}).values():
            f.edit.textChanged.connect(self._update_save_btn)
        if hasattr(self, '_backup_on_close'):
            self._backup_on_close.toggled.connect(self._update_save_btn)
        if hasattr(self, '_backup_retention_days'):
            self._backup_retention_days.valueChanged.connect(self._update_save_btn)
        if hasattr(self, '_backup_target_combo'):
            self._backup_target_combo.currentIndexChanged.connect(self._update_save_btn)
        if hasattr(self, '_backup_zip_password'):
            self._backup_zip_password.textChanged.connect(self._update_save_btn)
        if hasattr(self, '_nav_list_widget'):
            self._nav_list_widget.model().rowsMoved.connect(self._update_save_btn)

    @staticmethod
    def _flbl(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setFixedWidth(SETTINGS_LABEL_W)
        return lbl

    @staticmethod
    def _form(parent=None) -> QFormLayout:
        lay = QFormLayout(parent) if parent is not None else QFormLayout()
        lay.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lay.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        lay.setHorizontalSpacing(12)
        return lay

    # ------------------------------------------------------------ tab 1
    def _club_tab(self) -> QWidget:
        club = ss.get_club_profile()
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setSpacing(10)

        # "Verein" box: full width
        verein_box = QGroupBox("Verein")
        verein_form = self._form(verein_box)
        for key in ("club_name", "federation", "club_number"):
            edit = QLineEdit(club.get(key) or "")
            self.club_edits[key] = edit
            verein_form.addRow(self._flbl(CLUB_LABELS[key]), edit)
        lay.addWidget(verein_box)

        # 2-column grid for remaining boxes
        club_grid = QGridLayout()
        club_grid.setSpacing(10)
        club_grid.setColumnStretch(0, 1)
        club_grid.setColumnStretch(1, 1)

        for col, (box_title, keys) in enumerate([
            ("Adresse", ("street", "zip_code", "city", "country")),
            ("Kontakt", ("phone", "email", "website")),
        ]):
            box = QGroupBox(box_title)
            form = self._form(box)
            for key in keys:
                edit = QLineEdit(club.get(key) or "")
                self.club_edits[key] = edit
                form.addRow(self._flbl(CLUB_LABELS[key]), edit)
            club_grid.addWidget(box, 0, col)

        box_default_contact = QGroupBox("Standard-Kontaktperson")
        form_dc = self._form(box_default_contact)
        self._default_contact_combo = QComboBox()
        self._default_contact_combo.setFixedWidth(SETTINGS_COMBO_W)
        for role_key, role_label in CONTACT_ROLES.items():
            self._default_contact_combo.addItem(role_label, role_key)
        stored_role = ss.get("default_contact_role", "treasurer")
        idx = self._default_contact_combo.findData(stored_role)
        if idx >= 0:
            self._default_contact_combo.setCurrentIndex(idx)
        self.value_widgets["default_contact_role"] = self._default_contact_combo
        form_dc.addRow(self._flbl("Rolle"), self._default_contact_combo)
        club_grid.addWidget(box_default_contact, 1, 0)

        box_logo = QGroupBox("Logo")
        logo_lay = QHBoxLayout(box_logo)
        self._logo_path = club.get("logo_path") or ""
        self.logo_preview = QLabel()
        self.logo_preview.setFixedSize(LOGO_PREVIEW, LOGO_PREVIEW)
        self.logo_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo_preview.setFrameShape(QLabel.Shape.StyledPanel)
        logo_col = QVBoxLayout()
        row_btns = QHBoxLayout()
        row_btns.addWidget(button("Durchsuchen ...", self._browse_logo))
        row_btns.addWidget(button("Entfernen", self._remove_logo))
        row_btns.addStretch()
        logo_col.addLayout(row_btns)
        logo_col.addStretch()
        logo_lay.addLayout(logo_col, 1)
        logo_lay.addWidget(self.logo_preview)
        self._update_logo(self._logo_path)
        club_grid.addWidget(box_logo, 1, 1)

        lay.addLayout(club_grid)
        lay.addStretch()

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        return scroll

    def _contacts_tab(self) -> QWidget:
        club = ss.get_club_profile()
        inner = QWidget()
        grid = QGridLayout(inner)
        grid.setSpacing(10)
        roles = list(CONTACT_ROLES.items())
        for i, (role_key, role_label) in enumerate(roles):
            box = QGroupBox(role_label)
            form = self._form(box)
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
            row, col = divmod(i, 2)
            grid.addWidget(box, row, col)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        return scroll

    def _browse_logo(self):
        import shutil
        from bowtally import config
        path, _ = QFileDialog.getOpenFileName(self, "Logo auswählen", "",
                                              "Bilder (*.png *.jpg *.jpeg)")
        if not path:
            return
        dest = config.APP_DATA_DIR / Path(path).name
        shutil.copy2(path, dest)
        self._logo_path = str(dest)
        self._update_logo(self._logo_path)

    def _remove_logo(self):
        self._logo_path = ""
        self._update_logo("")

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
        self.mode.setFixedWidth(SETTINGS_COMBO_W)
        for key, label in ss.THEME_MODE_LABELS.items():
            self.mode.addItem(label, key)
        self.mode.setCurrentIndex(max(0, self.mode.findData(
            values.get(ss.KEY_UI_THEME_MODE) or "system")))
        self.mode.currentIndexChanged.connect(self._preview)
        mode_box = QGroupBox("Darstellung")
        mode_row = self._form(mode_box)
        mode_row.addRow(self._flbl("Darstellung"), self.mode)
        lay.addWidget(mode_box)

        self.color_fields: dict[str, ColorField] = {}
        boxes = {"brand": self._form(), "light": self._form(), "dark": self._form()}
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
        form = self._form(box)
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

    def _general_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)

        # Update-Prüfung
        box_update = QGroupBox("Update-Prüfung")
        form_update = self._form(box_update)
        self._update_check = QCheckBox("Beim Start nach Updates suchen")
        self._update_check.setChecked(ss.get_bool("update_check_enabled"))
        self._update_check.toggled.connect(
            lambda v: ss.set_value("update_check_enabled", "true" if v else "false"))

        from bowtally.updater.update_service import UpdateService
        service = UpdateService(config.APP_DATA_DIR)
        btn_manual = button("Jetzt prüfen", lambda: self._manual_update_check(service))
        self._last_check_label = QLabel(f"Letzte Prüfung: {service.last_check_str()}")
        self._last_check_label.setObjectName("pageSubtitle")
        right_col = QVBoxLayout()
        right_col.addWidget(btn_manual, alignment=Qt.AlignRight)
        right_col.addWidget(self._last_check_label, alignment=Qt.AlignRight)
        check_row = QHBoxLayout()
        check_row.addWidget(self._update_check, alignment=Qt.AlignVCenter)
        check_row.addStretch()
        check_row.addLayout(right_col)
        form_update.addRow("", check_row)
        lay.addWidget(box_update)

        # Speicherorte
        box_export = QGroupBox("Speicherorte")
        form_export = self._form(box_export)
        path_row = QHBoxLayout()
        path_row.setContentsMargins(0, 0, 0, 0)
        path_edit = QLineEdit(ss.get("default_export_path") or "")
        path_edit.setPlaceholderText("Leer lassen für Downloads-Ordner")
        path_edit.setMinimumWidth(SETTINGS_COMBO_W)
        path_btn = QPushButton("Durchsuchen …")
        path_btn.clicked.connect(lambda: _browse_export_path(path_edit, self))
        path_row.addWidget(path_edit, 1)
        path_row.addWidget(path_btn)
        path_widget = QWidget()
        path_widget.setLayout(path_row)
        form_export.addRow(self._flbl("Standard-Exportpfad"), path_widget)
        self.value_widgets["default_export_path"] = path_edit
        lay.addWidget(box_export)

        lay.addStretch()
        return w

    def _manual_update_check(self, service):
        info = service.check_for_update()
        self._last_check_label.setText(f"Letzte Prüfung: {service.last_check_str()}")
        if info is None or not info.available:
            from PySide6.QtWidgets import QMessageBox
            if service.last_error:
                QMessageBox.warning(self, "Update-Prüfung", service.last_error)
            else:
                QMessageBox.information(self, "Update-Prüfung", "Kein Update verfügbar.")
            return
        from bowtally.updater.update_dialog import UpdateDialog
        UpdateDialog(info, service, parent=self).exec()

    def _backup_tab(self) -> QWidget:
        from bowtally.services import backup_service as bs
        inner = QWidget()
        lay = QVBoxLayout(inner)

        # ---- Box 1: Backup-Einstellungen
        settings_box = QGroupBox("Backup-Einstellungen")
        settings_form = self._form(settings_box)
        self._backup_on_close = QCheckBox("Automatisches Backup beim Beenden der App")
        self._backup_on_close.setChecked(ss.get_bool("backup_on_close"))
        self._backup_retention_days = QSpinBox()
        self._backup_retention_days.setRange(1, 365)
        self._backup_retention_days.setValue(int(ss.get("backup_retention_days", "30") or 30))
        self._backup_retention_days.setSuffix(" Tage")
        self._backup_retention_days.setFixedWidth(SETTINGS_COMBO_W)
        self._backup_zip_password = QLineEdit(bs._get_password("backup_zip_password"))
        self._backup_zip_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._backup_zip_password.setPlaceholderText("Pflichtfeld")
        show_password = QCheckBox("Anzeigen")
        show_password.toggled.connect(lambda on: self._backup_zip_password.setEchoMode(
            QLineEdit.EchoMode.Normal if on else QLineEdit.EchoMode.Password))
        suggest_btn = button("Passwort vorschlagen", lambda: self._suggest_backup_password(show_password),
                             tooltip="Zufälliges Passwort erzeugen")
        password_row = QHBoxLayout()
        password_row.setContentsMargins(0, 0, 0, 0)
        password_row.addWidget(self._backup_zip_password, 1)
        password_row.addWidget(show_password)
        password_row.addWidget(suggest_btn)
        password_widget = QWidget()
        password_widget.setLayout(password_row)
        settings_form.addRow("", self._backup_on_close)
        settings_form.addRow(self._flbl("Aufbewahrungsdauer"), self._backup_retention_days)
        settings_form.addRow(self._flbl("Backup-Passwort *"), password_widget)
        settings_form.addRow("", QLabel("Backups sind mit diesem Passwort verschlüsselt. Es wird bei jeder "
                                        "Wiederherstellung benötigt und kann nicht wiederhergestellt werden "
                                        "– bitte notieren.", objectName="pageSubtitle", wordWrap=True))
        lay.addWidget(settings_box)

        # ---- Box 2: Backup-Speicherort
        target_box = QGroupBox("Backup-Speicherort")
        target_lay = QVBoxLayout(target_box)
        self._backup_target_combo = QComboBox()
        self._backup_target_combo.setFixedWidth(SETTINGS_COMBO_W)
        self._backup_target_combo.addItem("Lokal", "local")
        self._backup_target_combo.addItem("Netzwerk (NAS / Freigabe)", "network")
        self._backup_target_combo.addItem("Nextcloud", "nextcloud")
        saved = ss.get("backup_target") or (
            "nextcloud" if ss.get("backup_nextcloud_url") else "local")
        idx = self._backup_target_combo.findData(saved)
        self._backup_target_combo.setCurrentIndex(max(0, idx))
        _combo_form = self._form()
        _combo_form.addRow(self._flbl("Speicherart"), self._backup_target_combo)
        target_lay.addLayout(_combo_form)

        self._backup_stack = QStackedWidget()

        # Page 0: local
        local_w = QWidget()
        local_lay = QVBoxLayout(local_w)
        local_lay.setContentsMargins(0, 8, 0, 0)
        local_form = self._form()
        self._backup_path_edit = QLineEdit(ss.get("backup_local_path") or "")
        self._backup_path_edit.setPlaceholderText("Pfad zum Backup-Ordner …")
        browse_btn = self._menu_icon_button(lambda: self._browse_backup_path())
        path_row = QHBoxLayout()
        path_row.setContentsMargins(0, 0, 0, 0)
        path_row.setSpacing(8)
        path_row.addWidget(self._backup_path_edit, 1)
        path_row.addWidget(browse_btn)
        path_widget = QWidget()
        path_widget.setLayout(path_row)
        local_form.addRow(self._flbl("Verzeichnispfad"), path_widget)
        local_lay.addLayout(local_form)
        local_btns = QHBoxLayout()
        local_btns.setSpacing(8)
        local_btns.addWidget(button("Verbindung testen",
                                    lambda: self._test_backup(bs, "local"),
                                    tooltip="Schreibzugriff auf Verzeichnis prüfen"))
        local_btns.addWidget(button("Backup jetzt erstellen",
                                    lambda: self._do_backup_now(bs, "local"), "primary",
                                    "Datenbank als JSON sichern"))
        local_btns.addStretch()
        local_form.addRow("", local_btns)
        self._backup_stack.addWidget(local_w)

        # Page 1: network
        net_w = QWidget()
        net_lay = QVBoxLayout(net_w)
        net_lay.setContentsMargins(0, 8, 0, 0)
        net_form = self._form()
        self._net_path_edit = QLineEdit(ss.get("backup_network_path") or "")
        self._net_path_edit.setPlaceholderText(r"\\server\backup")
        net_form.addRow(self._flbl("Netzwerkpfad"), self._net_path_edit)
        self._net_auth_check = QCheckBox("Anmeldung erforderlich")
        self._net_auth_check.setChecked(ss.get_bool("backup_network_requires_auth"))
        net_form.addRow("", self._net_auth_check)
        net_lay.addLayout(net_form)
        self._net_auth_widget = QWidget()
        net_auth_form = self._form(self._net_auth_widget)
        net_auth_form.setContentsMargins(0, 0, 0, 0)
        self._net_user = QLineEdit(ss.get("backup_network_user") or "")
        self._net_pass = QLineEdit(bs._get_password("backup_network_password"))
        self._net_pass.setEchoMode(QLineEdit.EchoMode.Password)
        net_auth_form.addRow(self._flbl("Benutzername"), self._net_user)
        net_auth_form.addRow(self._flbl("Passwort"), self._net_pass)
        self._net_auth_widget.setVisible(self._net_auth_check.isChecked())
        self._net_auth_check.toggled.connect(self._net_auth_widget.setVisible)
        net_lay.addWidget(self._net_auth_widget)
        net_btns = QHBoxLayout()
        net_btns.setSpacing(8)
        net_btns.addWidget(button("Verbindung testen",
                                  lambda: self._test_backup(bs, "network"),
                                  tooltip="Netzwerkpfad auf Erreichbarkeit prüfen"))
        net_btns.addWidget(button("Backup jetzt erstellen",
                                  lambda: self._do_backup_now(bs, "network"), "primary",
                                  "Datenbank als JSON auf Netzlaufwerk sichern"))
        net_btns.addStretch()
        net_form.addRow("", net_btns)
        self._backup_stack.addWidget(net_w)

        # Page 2: nextcloud
        nc_w = QWidget()
        nc_lay = QVBoxLayout(nc_w)
        nc_lay.setContentsMargins(0, 8, 0, 0)
        nc_form = self._form()
        self._nc_url = QLineEdit(ss.get("backup_nextcloud_url") or "")
        self._nc_url.setPlaceholderText("https://ihre-nextcloud.de")
        self._nc_user = QLineEdit(ss.get("backup_nextcloud_user") or "")
        self._nc_pass = QLineEdit(bs._get_password("backup_nextcloud_password"))
        self._nc_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self._nc_path = QLineEdit(ss.get("backup_nextcloud_path") or "BowTally/Backups")
        self._nc_path.setPlaceholderText("/BowTally/Backups")
        nc_form.addRow(self._flbl("Server-URL"), self._nc_url)
        nc_form.addRow(self._flbl("Benutzername"), self._nc_user)
        nc_form.addRow(self._flbl("Passwort"), self._nc_pass)
        nc_form.addRow(self._flbl("Zielpfad"), self._nc_path)
        nc_lay.addLayout(nc_form)
        nc_btns = QHBoxLayout()
        nc_btns.setSpacing(8)
        nc_btns.addWidget(button("Verbindung testen",
                                 lambda: self._test_backup(bs, "nextcloud"),
                                 tooltip="WebDAV-Verbindung zu Nextcloud prüfen"))
        nc_btns.addWidget(button("Backup jetzt erstellen",
                                 lambda: self._do_backup_now(bs, "nextcloud"), "primary",
                                 "Backup in Nextcloud hochladen"))
        nc_btns.addStretch()
        nc_form.addRow("", nc_btns)
        self._backup_stack.addWidget(nc_w)

        self._backup_stack.setCurrentIndex(self._backup_target_combo.currentIndex())
        self._backup_target_combo.currentIndexChanged.connect(self._backup_stack.setCurrentIndex)
        target_lay.addWidget(self._backup_stack)
        lay.addWidget(target_box)

        # ---- Box 3: Wiederherstellen
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
        # Minimum = the box never shrinks below its size hint (no squeezed rows, no cut-off buttons);
        # the tab scrolls instead.
        for box in (settings_box, target_box, restore_box):
            box.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Minimum)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        return scroll

    def _suggest_backup_password(self, show_password: QCheckBox):
        import secrets
        alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"  # no 0/O/1/l/I
        self._backup_zip_password.setText("".join(secrets.choice(alphabet) for _ in range(20)))
        show_password.setChecked(True)

    def _browse_backup_path(self):
        path = QFileDialog.getExistingDirectory(self, "Backup-Ordner auswählen",
                                                self._backup_path_edit.text())
        if path:
            self._backup_path_edit.setText(path)

    def _backup_values(self) -> dict:
        return {
            "backup_on_close": "true" if self._backup_on_close.isChecked() else "false",
            "backup_retention_days": str(self._backup_retention_days.value()),
            "backup_target": self._backup_target_combo.currentData(),
            "backup_local_path": self._backup_path_edit.text().strip(),
            "backup_network_path": self._net_path_edit.text().strip(),
            "backup_network_requires_auth":
                "true" if self._net_auth_check.isChecked() else "false",
            "backup_network_user": self._net_user.text().strip(),
            "backup_nextcloud_url": self._nc_url.text().strip(),
            "backup_nextcloud_user": self._nc_user.text().strip(),
            "backup_nextcloud_path": self._nc_path.text().strip(),
            "backup_network_password": self._net_pass.text(),
            "backup_nextcloud_password": self._nc_pass.text(),
            "backup_zip_password": self._backup_zip_password.text(),
        }

    def _save_backup_settings(self, password_required: bool = True):
        from bowtally.services import backup_service as bs
        values = self._backup_values()
        if password_required and not values["backup_zip_password"]:
            raise ValidationError("Bitte unter Backup ein Backup-Passwort festlegen.")
        bs._set_password("backup_zip_password", values.pop("backup_zip_password"))
        bs._set_password("backup_network_password", values.pop("backup_network_password"))
        bs._set_password("backup_nextcloud_password", values.pop("backup_nextcloud_password"))
        ss.set_many(values)

    def _test_backup(self, bs, target: str):
        from bowtally.ui.components.toast import Toast
        try:
            self._save_backup_settings()
            if target == "local":
                bs.test_local(self._backup_path_edit.text().strip())
            elif target == "network":
                bs.test_network(
                    self._net_path_edit.text().strip(),
                    self._net_auth_check.isChecked(),
                    self._net_user.text().strip(),
                    self._net_pass.text(),
                )
            else:
                bs.test_nextcloud(
                    self._nc_url.text().strip(),
                    self._nc_user.text().strip(),
                    self._nc_pass.text(),
                    self._nc_path.text().strip(),
                )
        except Exception as exc:
            Toast.show(self, str(exc), Toast.ERROR)
            return
        Toast.show(self, "Verbindung erfolgreich", Toast.SUCCESS)

    def _do_backup_now(self, bs, target: str):
        from bowtally.ui.components.toast import Toast
        try:
            self._save_backup_settings()
            if target == "local":
                result = bs.backup_local()
                Toast.show(self, f"Backup erstellt: {result}", Toast.SUCCESS)
            elif target == "network":
                result = bs.backup_network()
                Toast.show(self, f"Backup erstellt: {result}", Toast.SUCCESS)
            else:
                bs.backup_nextcloud()
                Toast.show(self, "Backup zu Nextcloud hochgeladen", Toast.SUCCESS)
        except Exception as exc:
            show_error(self, exc, "Backup fehlgeschlagen")

    def _do_restore(self, bs):
        path, _ = QFileDialog.getOpenFileName(self, "Backup auswählen", "",
                                               "BowTally-Backup (*.zip)")
        if not path:
            return
        from bowtally.ui.components.confirm_dialog import ConfirmDialog
        if not ConfirmDialog.ask(self, "Datenbank wiederherstellen?",
                                 "Die aktuelle Datenbank wird durch das Backup ersetzt.\n"
                                 "Dieser Vorgang kann nicht rückgängig gemacht werden.",
                                 "Wiederherstellen", destructive=True):
            return
        password, prompt = None, ""
        while True:
            try:
                bs.restore(path, password)
                break
            except bs.BackupPasswordRequired:
                prompt = "Passwort des Backups:"
            except bs.BackupPasswordWrong:
                prompt = "Das Passwort ist falsch. Bitte erneut eingeben:"
            except Exception as exc:
                show_error(self, exc, "Wiederherstellung fehlgeschlagen")
                return
            password, accepted = QInputDialog.getText(self, "Backup-Passwort", prompt,
                                                      QLineEdit.EchoMode.Password)
            if not accepted:
                return
        from bowtally.ui.components.toast import Toast
        Toast.show(self, "Backup wiederhergestellt – bitte Anwendung neu starten", Toast.SUCCESS)

    def _print_tab(self) -> QWidget:
        club = ss.get_club_profile()
        edit_course = QPlainTextEdit(club.get("course_description") or "")
        edit_course.setMinimumHeight(90)
        edit_course.setPlaceholderText(
            "z. B. Waldparcours ca. 4 km, festes Schuhwerk erforderlich")
        self.club_edits["course_description"] = edit_course
        inner = QWidget()
        lay = QVBoxLayout(inner)

        # Collect print/templates boxes without adding to lay yet
        cat_boxes: dict[str, QGroupBox] = {}
        groups: dict[str, QFormLayout] = {}
        for st in self.settings:
            if st.value_type == "color" or st.key == ss.KEY_UI_THEME_MODE \
                    or st.key in HIDDEN_KEYS \
                    or st.category not in ("print", "templates") \
                    or st.category in HIDDEN_CATEGORIES:
                continue
            if st.category not in groups:
                box = QGroupBox(CATEGORY_LABELS.get(st.category, st.category or "Allgemein"))
                cat_boxes[st.category] = box
                groups[st.category] = self._form(box)
                if st.category == "templates":
                    lbl = self._flbl("Parcours-Beschreibung")
                    lbl.setWordWrap(True)
                    groups["templates"].addRow(lbl, _with_grip(edit_course))
            widget = self._widget_for(st)
            self.value_widgets[st.key] = widget
            display = _with_grip(widget) if isinstance(widget, QPlainTextEdit) else widget
            label = self._flbl(LABEL_OVERRIDES.get(st.key) or st.description or st.key)
            label.setWordWrap(True)
            label.setToolTip(st.key)
            groups[st.category].addRow(label, display)

        if "print" in cat_boxes:
            lay.addWidget(cat_boxes["print"])
        if "templates" in cat_boxes:
            lay.addWidget(cat_boxes["templates"])
        lay.addStretch()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        return scroll

    # ------------------------------------------------------------ email templates tab
    def _email_tab(self) -> QWidget:
        values = {st.key: st.value or "" for st in self.settings}
        inner = QWidget()
        lay = QVBoxLayout(inner)
        lay.setSpacing(10)
        hint = QLabel("Platzhalter: {name}, {verein}, {klasse}, {turniername}, {datum}",
                      objectName="pageSubtitle")
        lay.addWidget(hint)
        for title, subj_key, body_key in (
            ("Anmeldebestätigung", "email_reg_subject", "email_reg_body"),
            ("Zahlungserinnerung", "email_payment_subject", "email_payment_body"),
            ("Startunterlagen", "email_docs_subject", "email_docs_body"),
            ("Ergebnisversand", "email_results_subject", "email_results_body"),
            ("Wartelisten-Nachrücker", "email_waitlist_subject", "email_waitlist_body"),
            ("Helfer-Bestätigung", "email_helper_subject", "email_helper_body"),
            ("Turnier-Ankündigung", "email_tpl_tournament_announce_subject",
             "email_tpl_tournament_announce_body"),
        ):
            box = QGroupBox(title)
            form = self._form(box)
            subj = QLineEdit(values.get(subj_key, ""))
            body = QPlainTextEdit(values.get(body_key, ""))
            body.setMinimumHeight(90)
            self.value_widgets[subj_key] = subj
            self.value_widgets[body_key] = body
            form.addRow(self._flbl("Betreff"), subj)
            form.addRow(self._flbl("Text"), _with_grip(body))
            lay.addWidget(box)
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
                groups[st.category] = self._form(box)
                lay.addWidget(box)
            widget = self._widget_for(st)
            self.value_widgets[st.key] = widget
            display = _with_grip(widget) if isinstance(widget, QPlainTextEdit) else widget
            label = self._flbl(LABEL_OVERRIDES.get(st.key) or st.description or st.key)
            label.setWordWrap(True)
            label.setToolTip(st.key)
            groups[st.category].addRow(label, display)
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
            w.setFixedWidth(SETTINGS_COMBO_W)
        elif st.category in MULTILINE_CATEGORIES:
            w = QPlainTextEdit(value)
            w.setMinimumHeight(90)
        elif st.key in ss.OPTIONS:
            w = QComboBox()
            display = COMBO_LABELS.get(st.key, {})
            for val in ss.OPTIONS[st.key]:
                w.addItem(display.get(val, val), val)
            idx = w.findData(value) if value else -1
            w.setCurrentIndex(idx if idx >= 0 else 0)
            w.setFixedWidth(SETTINGS_COMBO_W)
        elif st.value_type == "path":
            w = QWidget()
            w.edit = QLineEdit(value)
            row = QHBoxLayout(w)
            row.setContentsMargins(0, 0, 0, 0)
            row.addWidget(w.edit)
            row.addWidget(self._menu_icon_button(lambda _=False, e=w.edit: self._browse_path(e)))
        else:
            w = QLineEdit(value)
        return w

    @staticmethod
    def _menu_icon_button(slot) -> QPushButton:
        """Schmaler Button mit Hamburger-Icon (≡) für die Pfadauswahl."""
        return burger_button("Durchsuchen", slot)

    def _nav_tab(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        self._nav_list_widget = QListWidget()
        self._nav_list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        self._nav_list_widget.setDefaultDropAction(Qt.DropAction.MoveAction)
        self._nav_list_widget.setAlternatingRowColors(True)
        raw = ss.get("nav_order") or ""
        try:
            saved = json.loads(raw) if raw else []
        except Exception:
            saved = []
        # handle both old string format and new dict format
        if saved and isinstance(saved[0], str):
            saved = [{"key": k, "visible": True} for k in saved]
        vis_map = {e["key"]: e.get("visible", True) for e in saved if isinstance(e, dict)}
        ordered = [e["key"] for e in saved if isinstance(e, dict) and e["key"] in NAV_LABELS]
        ordered += [k for k in NAV_KEYS if k not in ordered]
        for key in ordered:
            self._add_nav_item(key, vis_map.get(key, True))
        reset_btn = button("Standardreihenfolge wiederherstellen", self._reset_nav_order)
        hint = QLabel("Änderungen werden nach Neustart der App wirksam.",
                      objectName="pageSubtitle")
        lay.addWidget(self._nav_list_widget, 1)
        lay.addWidget(reset_btn)
        lay.addWidget(hint)
        return w

    def _add_nav_item(self, key: str, visible: bool) -> None:
        t = theme.current()
        muted = t["text2"]
        locked = key in NAV_LOCKED
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, key)
        item.setData(VISIBLE_ROLE, visible)
        item.setSizeHint(QSize(0, 36))
        self._nav_list_widget.addItem(item)
        self._nav_list_widget.setItemWidget(item, self._make_nav_row(key, visible, locked))

    def _make_nav_row(self, key: str, visible: bool, locked: bool) -> QWidget:
        t = theme.current()
        muted = t["text2"]
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(4, 0, 4, 0)
        h.setSpacing(6)
        grip = QLabel()
        grip.setPixmap(theme.pixmap("grip", muted, 16))
        h.addWidget(grip)
        lbl = QLabel(NAV_LABELS[key])
        if not visible:
            lbl.setStyleSheet(f"color:{muted};")
        h.addWidget(lbl, 1)
        eye_btn = QToolButton()
        eye_icon = "eye" if visible else "eye-off"
        eye_color = t["primary"] if visible else muted
        eye_btn.setIcon(QIcon(theme.pixmap(eye_icon, eye_color, 16)))
        if locked:
            eye_btn.setEnabled(False)
            eye_btn.setToolTip("Dieser Eintrag kann nicht ausgeblendet werden")
        else:
            eye_btn.setToolTip("Ausblenden" if visible else "Einblenden")
            eye_btn.clicked.connect(lambda _=False, k=key: self._toggle_nav_visibility(k))
        h.addWidget(eye_btn)
        return w

    def _toggle_nav_visibility(self, key: str) -> None:
        for i in range(self._nav_list_widget.count()):
            item = self._nav_list_widget.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == key:
                new_vis = not bool(item.data(VISIBLE_ROLE))
                item.setData(VISIBLE_ROLE, new_vis)
                locked = key in NAV_LOCKED
                self._nav_list_widget.setItemWidget(item, self._make_nav_row(key, new_vis, locked))
                self._update_save_btn()
                return

    def _reset_nav_order(self):
        self._nav_list_widget.clear()
        for key in NAV_KEYS:
            self._add_nav_item(key, True)
        self._update_save_btn()

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
        self._close_dialog()
