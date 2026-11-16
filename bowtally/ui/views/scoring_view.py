# -*- coding: utf-8 -*-
"""Score entry grid: rows = participants, columns = targets (x shots).

Three views share one model: frozen left (start number, name, class), scrollable middle
(scores) and frozen right (total). Every committed cell is saved immediately.

Keyboard: Tab / Shift+Tab horizontal, Enter / Down next participant, Up previous,
Escape cancels the edit. Focusing a cell starts editing and opens the zone list.
"""
from datetime import datetime

from PySide6.QtCore import QModelIndex, QPersistentModelIndex, QStringListModel, Qt, QTimer, \
    Signal
from PySide6.QtGui import QBrush, QColor, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (QAbstractItemDelegate, QAbstractItemView, QCheckBox, QComboBox,
                               QCompleter,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMenu,
                               QStackedWidget, QStyledItemDelegate, QTabBar, QTableView,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from shiboken6 import isValid

from bowtally.services import scoring_service as sc
from bowtally.ui import busy, button, show_error, theme
from bowtally.ui.components.confirm_dialog import ConfirmDialog
from bowtally.ui.components.data_table import ROW_HEIGHT
from bowtally.ui.components.search_bar import SearchBar
from bowtally.ui.components.toast import Toast

FIXED = 3                                 # start number, name, class
CELL_ROLE = Qt.ItemDataRole.UserRole + 1  # (participant_id, target, shot)
CLASS_ROLE = Qt.ItemDataRole.UserRole + 2
GROUP_ROLE = Qt.ItemDataRole.UserRole + 3
ZONE_ROLE  = Qt.ItemDataRole.UserRole + 4  # zone_hit string for specials aggregation
ALL = "__all__"
HIDDEN_BAR_QSS = ("QScrollBar { background: transparent; } "
                  "QScrollBar::handle { background: transparent; }")


def zone_label(z: dict) -> str:
    return f"{z['zone']} ({z['points']})"


class ScoreDelegate(QStyledItemDelegate):
    """Line edit with zone completer; handles vertical navigation keys."""
    moveRequested = Signal(QPersistentModelIndex, int)   # index, row delta

    def __init__(self, zones: list[dict], parent=None):
        super().__init__(parent)
        self.labels = [zone_label(z) for z in zones]
        self._editor = None
        self._index = None

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        completer = QCompleter(QStringListModel(self.labels, editor), editor)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setFilterMode(Qt.MatchFlag.MatchContains)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        completer.setMaxVisibleItems(len(self.labels))
        editor.setCompleter(completer)
        completer.activated[str].connect(lambda text: self._pick(editor, text))
        completer.popup().installEventFilter(self)
        editor.installEventFilter(self)
        editor.destroyed.connect(self._forget)
        self._editor, self._index = editor, QPersistentModelIndex(index)
        QTimer.singleShot(0, lambda: self._show_all(editor))
        return editor

    def _forget(self, *_):
        self._editor = None

    def _show_all(self, editor):
        if editor is self._editor and isValid(editor) and editor.hasFocus()                 and editor.completer():
            editor.completer().setCompletionPrefix("")
            editor.completer().complete()

    def setEditorData(self, editor, index):
        editor.setText(index.data() or "")
        editor.selectAll()

    def setModelData(self, editor, model, index):
        model.setData(index, editor.text().strip())

    def _pick(self, editor, text):
        editor.setText(text)
        self._commit_and_move(editor, 1)

    def _commit_and_move(self, editor, delta: int):
        index = self._index
        self.commitData.emit(editor)
        self.closeEditor.emit(editor, QAbstractItemDelegate.EndEditHint.NoHint)
        self.moveRequested.emit(index, delta)

    def eventFilter(self, obj, event):
        editor = self._editor
        if event.type() != event.Type.KeyPress or editor is None or not isValid(editor)                 or (obj is not editor and obj is not editor.completer().popup()):
            return False if obj is not editor else super().eventFilter(obj, event)
        popup = editor.completer().popup() if editor.completer() else None
        key = event.key()
        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if obj is popup and popup.currentIndex().isValid():
                editor.setText(popup.currentIndex().data())
            if popup is not None:
                popup.hide()
            self._commit_and_move(editor, 1)
            return True
        if key in (Qt.Key.Key_Down, Qt.Key.Key_Up):
            if popup is not None:
                popup.hide()
            self._commit_and_move(editor, 1 if key == Qt.Key.Key_Down else -1)
            return True
        if key == Qt.Key.Key_Escape:
            # discard the input; keep the focus in the grid (not in the next widget)
            if popup is not None:
                popup.hide()
            self.closeEditor.emit(editor, QAbstractItemDelegate.EndEditHint.RevertModelCache)
            self.parent().setFocus()
            return True
        if obj is popup and key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab):
            popup.hide()
            return super().eventFilter(editor, event)
        if obj is popup:
            return False
        return super().eventFilter(obj, event)


def _frozen_view(model) -> QTableView:
    v = QTableView()
    v.setModel(model)
    v.verticalHeader().hide()
    v.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
    v.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
    v.horizontalHeader().setFixedHeight(36)
    v.horizontalHeader().setHighlightSections(False)
    v.setAlternatingRowColors(True)
    v.setWordWrap(False)
    v.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
    return v


class ScoringView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.tournament = None
        self._loading = False
        self._stay = None
        self._current_round = 1
        self.cols: list[tuple[int, int]] = []
        self._tracked_keys: list[str] = []
        self._spec_labels: list[str] = []
        self._zone_type_map: dict[str, str] = {}
        self.model = QStandardItemModel(self)
        self.model.itemChanged.connect(self._on_changed)

        self.left, self.mid, self.right = (_frozen_view(self.model) for _ in range(3))
        for v in (self.left, self.right):
            v.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            v.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
            v.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            v.horizontalScrollBar().setStyleSheet(HIDDEN_BAR_QSS)
        self.left.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mid.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.mid.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.mid.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.mid.setTabKeyNavigation(True)
        bars = [v.verticalScrollBar() for v in (self.left, self.mid, self.right)]
        for a in bars:
            for b in bars:
                if a is not b:
                    a.valueChanged.connect(b.setValue)
        header = self.mid.horizontalHeader()
        header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        header.customContextMenuRequested.connect(self._header_menu)
        header.setToolTip("Rechtsklick: Scheibe für alle sichtbaren Teilnehmer setzen")

        self.class_tabs = QTabBar()
        self.class_tabs.setDrawBase(False)
        self.class_tabs.setExpanding(False)
        self.class_tabs.currentChanged.connect(lambda _i: self._apply_filter())
        self.group_filter = QComboBox()
        self.group_filter.setToolTip("Nach Startgruppe filtern")
        self.group_filter.currentIndexChanged.connect(lambda _i: self._apply_filter())
        self.search = SearchBar("Name oder Startnummer …")
        self.search.searchChanged.connect(lambda _t: self._apply_filter())
        self.incomplete_only = QCheckBox("Nur unvollständige")
        self.incomplete_only.setToolTip("Nur Teilnehmer mit fehlenden Scheibenergebnissen")
        self.incomplete_only.toggled.connect(lambda _v: self._apply_filter())
        self.save_btn = button("Speichern", self.save, "primary",
                               "Alle Eingaben speichern (Strg+S). Jede Zelle wird zusätzlich "
                               "sofort beim Verlassen gespeichert.")

        # round selector – only visible for per_target multi-round
        self.round_bar = QTabBar()
        self.round_bar.setDrawBase(False)
        self.round_bar.setExpanding(False)
        self.round_bar.currentChanged.connect(self._on_round_changed)

        bar = QHBoxLayout()
        bar.addWidget(self.group_filter)
        bar.addWidget(self.incomplete_only)
        bar.addWidget(self.class_tabs, 1)
        bar.addWidget(self.search)
        bar.addWidget(self.save_btn)

        grid = QHBoxLayout()
        grid.setSpacing(0)
        grid.addWidget(self.left)
        grid.addWidget(self.mid, 1)
        grid.addWidget(self.right)

        # per_target grid widget (page 0)
        self._grid_widget = QWidget()
        gl = QVBoxLayout(self._grid_widget)
        gl.setContentsMargins(0, 0, 0, 0)
        gl.setSpacing(0)
        gl.addLayout(bar)
        gl.addLayout(grid, 1)

        # simple table for per_round / total_only (page 1)
        self._simple_table = QTableWidget()
        self._simple_table.verticalHeader().hide()
        self._simple_table.horizontalHeader().setStretchLastSection(True)
        self._simple_table.setAlternatingRowColors(True)
        self._simple_table.setWordWrap(False)
        self._simple_table.itemChanged.connect(self._on_simple_changed)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._grid_widget)
        self._stack.addWidget(self._simple_table)

        self.hint = QLabel(objectName="pageSubtitle")
        self.hint.setWordWrap(True)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 12, 0, 0)
        lay.addWidget(self.round_bar)
        lay.addWidget(self._stack, 1)
        lay.addWidget(self.hint)
        theme.notifier.changed.connect(self._recolor_all)

    def _on_round_changed(self, idx: int):
        if self.tournament is None or idx < 0:
            return
        self._current_round = self.round_bar.tabData(idx) or 1
        self._load_per_target()

    def _scoring_mode(self) -> str:
        return getattr(self.tournament, "scoring_mode", "per_target") or "per_target"

    def _num_rounds(self) -> int:
        return getattr(self.tournament, "num_rounds", 1) or 1

    def _round_labels(self) -> list[str]:
        rounds = getattr(self.tournament, "rounds", []) or []
        if rounds:
            return [r.label for r in sorted(rounds, key=lambda r: r.round_number)]
        return [f"{i}. Runde" for i in range(1, self._num_rounds() + 1)]

    # ------------------------------------------------------------ build
    def set_tournament(self, t):
        self.tournament = t
        mode = self._scoring_mode()
        num_rounds = self._num_rounds()

        # build round bar
        self.round_bar.blockSignals(True)
        while self.round_bar.count():
            self.round_bar.removeTab(0)
        if mode == "per_target" and num_rounds > 1:
            for i, lbl in enumerate(self._round_labels(), start=1):
                idx = self.round_bar.addTab(lbl)
                self.round_bar.setTabData(idx, i)
            # keep current round if still valid
            if self._current_round > num_rounds:
                self._current_round = 1
            for i in range(self.round_bar.count()):
                if self.round_bar.tabData(i) == self._current_round:
                    self.round_bar.setCurrentIndex(i)
        else:
            self._current_round = 1
        self.round_bar.setVisible(mode == "per_target" and num_rounds > 1)
        self.round_bar.blockSignals(False)

        if mode == "per_target":
            self._stack.setCurrentIndex(0)
            self._load_per_target()
        elif mode == "per_round":
            self._stack.setCurrentIndex(1)
            self._load_per_round()
        else:  # total_only
            self._stack.setCurrentIndex(1)
            self._load_total_only()

    def _load_per_target(self):
        t = self.tournament
        self.zones = t.scoring_rule.ring_values if t.scoring_rule else []
        self.top_points = max((z["points"] for z in self.zones), default=None)
        self.delegate = ScoreDelegate(self.zones, self.mid)
        self.delegate.moveRequested.connect(self._move)
        self.mid.setItemDelegate(self.delegate)
        shots = t.shots_per_target
        self.cols = [(tg, s) for tg in range(1, t.num_targets + 1) for s in range(1, shots + 1)]
        _rule = t.scoring_rule
        _tracked = [sp for sp in (_rule.tracked_specials or []) if sp.get("track")] if _rule else []
        self._tracked_keys = [sp["key"] for sp in _tracked]
        self._spec_labels = [sp["label"] for sp in _tracked]
        self._zone_type_map = {z["zone"]: (z.get("type") or "") for z in self.zones}
        headers = ["Nr.", "Name", "Klasse"] + [
            str(tg) if shots == 1 else f"{tg}.{s}" for tg, s in self.cols
        ] + self._spec_labels + ["Gesamt"]
        with busy():
            scores = sc.get_scores(t.id, self._current_round)
        parts = sorted(t.participants, key=lambda p: (p.start_number or 10**9,
                                                      p.archer.last_name))
        locked = t.status == "closed"
        right_align = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        self._loading = True
        self.model.clear()
        self.model.setHorizontalHeaderLabels(headers)
        for p in parts:
            row = []
            for text in (str(p.start_number or ""), f"{p.archer.last_name}, {p.archer.first_name}",
                         (p.bow_class.abbreviation or p.bow_class.name) if p.bow_class else "–"):
                it = QStandardItem(text)
                it.setEditable(False)
                it.setData(p.bow_class_id, CLASS_ROLE)
                it.setData(p.start_group or "", GROUP_ROLE)
                row.append(it)
            row[0].setTextAlignment(right_align)
            for tg, s in self.cols:
                score = scores.get((p.id, tg, s))
                it = QStandardItem("" if score is None else str(score.points))
                it.setTextAlignment(right_align)
                it.setData((p.id, tg, s), CELL_ROLE)
                it.setEditable(not locked)
                zone_hit = score.zone_hit if score else None
                if zone_hit:
                    it.setToolTip(zone_hit)
                it.setData(zone_hit, ZONE_ROLE)
                row.append(it)
            for _ in self._tracked_keys:
                spec_it = QStandardItem()
                spec_it.setEditable(False)
                spec_it.setTextAlignment(right_align)
                row.append(spec_it)
            total = QStandardItem()
            total.setEditable(False)
            total.setTextAlignment(right_align)
            f = total.font()
            f.setBold(True)
            total.setFont(f)
            row.append(total)
            self.model.appendRow(row)
            self._update_right_cols(self.model.rowCount() - 1)
        self._loading = False
        self._recolor_all()

        spec_start = FIXED + len(self.cols)
        last = len(headers) - 1
        for c in range(len(headers)):
            self.left.setColumnHidden(c, c >= FIXED)
            self.mid.setColumnHidden(c, c < FIXED or c >= spec_start)
            self.right.setColumnHidden(c, c < spec_start)
        self.left.resizeColumnsToContents()
        self.left.setColumnWidth(1, max(self.left.columnWidth(1), 160))
        self.left.setFixedWidth(sum(self.left.columnWidth(c) for c in range(FIXED)) + 2)
        _spec_w = 48
        _sb_w = self.right.verticalScrollBar().sizeHint().width()
        for i in range(len(self._tracked_keys)):
            self.right.setColumnWidth(spec_start + i, _spec_w)
        self.right.setColumnWidth(last, 76)
        self.right.setFixedWidth(len(self._tracked_keys) * _spec_w + 76 + _sb_w + 2)
        for c in range(FIXED, last):
            self.mid.setColumnWidth(c, 52)
        self.mid.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers if locked else
            QAbstractItemView.EditTrigger.CurrentChanged
            | QAbstractItemView.EditTrigger.AnyKeyPressed
            | QAbstractItemView.EditTrigger.DoubleClicked)
        self.save_btn.setEnabled(not locked)

        current_cls = self.class_tabs.tabData(self.class_tabs.currentIndex()) \
            if self.class_tabs.count() else ALL
        self.class_tabs.blockSignals(True)
        while self.class_tabs.count():
            self.class_tabs.removeTab(0)
        self.class_tabs.addTab(f"Alle ({len(parts)})")
        self.class_tabs.setTabData(0, ALL)
        for bc in t.bow_classes:
            n = sum(p.bow_class_id == bc.id for p in parts)
            if n:
                i = self.class_tabs.addTab(f"{bc.abbreviation or bc.name} ({n})")
                self.class_tabs.setTabData(i, bc.id)
                self.class_tabs.setTabToolTip(i, bc.name)
        for i in range(self.class_tabs.count()):
            if self.class_tabs.tabData(i) == current_cls:
                self.class_tabs.setCurrentIndex(i)
        self.class_tabs.blockSignals(False)
        groups = sorted({p.start_group for p in parts if p.start_group})
        current_grp = self.group_filter.currentData()
        self.group_filter.blockSignals(True)
        self.group_filter.clear()
        self.group_filter.addItem("Alle Gruppen", ALL)
        for g in groups:
            self.group_filter.addItem(f"Gruppe {g}", g)
        self.group_filter.setCurrentIndex(max(0, self.group_filter.findData(current_grp)))
        self.group_filter.setVisible(bool(groups))
        self.group_filter.blockSignals(False)
        self._apply_filter()

        self.hint.setText(
            "Turnier abgeschlossen – Eingaben gesperrt." if locked else
            "Zahl tippen oder Zone wählen · Enter/↓ nächster Teilnehmer · ↑ vorheriger · "
            "Tab nächste Scheibe · Esc verwirft die Eingabe · jede Zelle wird sofort gespeichert")

    # ------------------------------------------------------------ cell logic
    def _score_columns(self):
        return range(FIXED, FIXED + len(self.cols))

    def _recolor(self, item: QStandardItem):
        t = theme.current()
        text = item.text()
        if text and self.top_points and text == str(self.top_points):
            item.setBackground(QBrush(QColor(t["success_soft"])))
        elif text == "0":
            item.setBackground(QBrush(QColor(t["miss_soft"])))
        else:
            item.setBackground(QBrush())

    def _recolor_all(self):
        if not self.cols:
            return
        was, self._loading = self._loading, True
        for r in range(self.model.rowCount()):
            for c in self._score_columns():
                self._recolor(self.model.item(r, c))
        self._loading = was

    def _update_right_cols(self, row: int):
        score_cols = self._score_columns()
        total = sum(int(self.model.item(row, c).text()) for c in score_cols
                    if self.model.item(row, c).text().lstrip("-").isdigit())
        spec_start = FIXED + len(self.cols)
        last = spec_start + len(self._tracked_keys)
        self.model.item(row, last).setText(str(total))
        if self._tracked_keys:
            counts = {k: 0 for k in self._tracked_keys}
            for c in score_cols:
                zone = self.model.item(row, c).data(ZONE_ROLE)
                if zone:
                    zt = self._zone_type_map.get(zone, "")
                    if zt in counts:
                        counts[zt] += 1
            for i, k in enumerate(self._tracked_keys):
                v = counts[k]
                self.model.item(row, spec_start + i).setText(str(v) if v else "")

    def _on_changed(self, item: QStandardItem):
        if self._loading or item.data(CELL_ROLE) is None:
            return
        pid, target, shot = item.data(CELL_ROLE)
        rnd = self._current_round
        self._loading = True
        try:
            entry = sc.parse_entry(item.text(), self.zones)
            sc.set_score(pid, target, shot, entry, round_number=rnd)
            item.setText("" if entry is None else str(entry[0]))
            zone_hit = entry[1] if entry else None
            item.setToolTip(zone_hit or "")
            item.setData(zone_hit, ZONE_ROLE)
            self._mark_saved()
        except Exception as exc:
            show_error(self, exc)
            stored = sc.get_scores(self.tournament.id, rnd).get((pid, target, shot))
            item.setText("" if stored is None else str(stored.points))
            self._stay = QPersistentModelIndex(item.index())
        finally:
            self._recolor(item)
            self._update_right_cols(item.row())
            self._loading = False

    # ---- per_round / total_only simple table ----------------------------
    def _load_per_round(self):
        t = self.tournament
        num_rounds = self._num_rounds()
        labels = self._round_labels()
        locked = t.status == "closed"
        parts = sorted(t.participants, key=lambda p: (p.start_number or 10**9,
                                                      p.archer.last_name))
        with busy():
            all_sc = sc.get_all_scores(t.id)
        self._simple_table.blockSignals(True)
        self._simple_table.setColumnCount(4 + num_rounds + 1)
        headers = ["Nr.", "Name", "Verein", "Klasse"] + labels + ["Gesamt"]
        self._simple_table.setHorizontalHeaderLabels(headers)
        self._simple_table.setRowCount(len(parts))
        right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        for row, p in enumerate(parts):
            for col, txt in enumerate([str(p.start_number or ""),
                                       f"{p.archer.last_name}, {p.archer.first_name}",
                                       p.archer.club or "",
                                       p.bow_class.name if p.bow_class else "–"]):
                it = QTableWidgetItem(txt)
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(right)
                self._simple_table.setItem(row, col, it)
            grand = 0
            for rn in range(1, num_rounds + 1):
                sc_entry = all_sc.get((p.id, rn, 0, 1))
                pts = sc_entry.points if sc_entry else None
                it = QTableWidgetItem("" if pts is None else str(pts))
                it.setTextAlignment(right)
                it.setData(Qt.ItemDataRole.UserRole, (p.id, rn))
                if locked:
                    it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self._simple_table.setItem(row, 4 + rn - 1, it)
                grand += pts or 0
            total_it = QTableWidgetItem(str(grand))
            total_it.setFlags(Qt.ItemFlag.ItemIsEnabled)
            total_it.setTextAlignment(right)
            f = total_it.font()
            f.setBold(True)
            total_it.setFont(f)
            self._simple_table.setItem(row, 4 + num_rounds, total_it)
        self._simple_table.blockSignals(False)
        self._simple_table.resizeColumnsToContents()
        for c in range(4, 4 + num_rounds):
            self._simple_table.setColumnWidth(c, max(80, self._simple_table.columnWidth(c)))
        self.save_btn.setEnabled(not locked)
        self.hint.setText("Turnier abgeschlossen – Eingaben gesperrt." if locked else
                          "Gesamtpunkte je Runde direkt eintragen · jede Zelle wird sofort gespeichert")

    def _load_total_only(self):
        t = self.tournament
        locked = t.status == "closed"
        parts = sorted(t.participants, key=lambda p: (p.start_number or 10**9,
                                                      p.archer.last_name))
        with busy():
            all_sc = sc.get_all_scores(t.id)
        self._simple_table.blockSignals(True)
        self._simple_table.setColumnCount(5)
        self._simple_table.setHorizontalHeaderLabels(["Nr.", "Name", "Verein", "Klasse", "Gesamt"])
        self._simple_table.setRowCount(len(parts))
        right = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        for row, p in enumerate(parts):
            for col, txt in enumerate([str(p.start_number or ""),
                                       f"{p.archer.last_name}, {p.archer.first_name}",
                                       p.archer.club or "",
                                       p.bow_class.name if p.bow_class else "–"]):
                it = QTableWidgetItem(txt)
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
                it.setTextAlignment(right)
                self._simple_table.setItem(row, col, it)
            sc_entry = all_sc.get((p.id, 0, 0, 1))
            pts = sc_entry.points if sc_entry else None
            it = QTableWidgetItem("" if pts is None else str(pts))
            it.setTextAlignment(right)
            it.setData(Qt.ItemDataRole.UserRole, (p.id, 0))  # round 0 = total_only
            if locked:
                it.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self._simple_table.setItem(row, 4, it)
        self._simple_table.blockSignals(False)
        self._simple_table.resizeColumnsToContents()
        self.save_btn.setEnabled(not locked)
        self.hint.setText("Turnier abgeschlossen – Eingaben gesperrt." if locked else
                          "Gesamtpunkte direkt eintragen · jede Zelle wird sofort gespeichert")

    def _on_simple_changed(self, item: QTableWidgetItem):
        if self._simple_table.signalsBlocked():
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if data is None:
            return
        pid, rnd = data
        text = item.text().strip()
        try:
            if not text:
                sc.set_score(pid, 0, 1, None, round_number=rnd)
                self._update_simple_total(item.row())
                self._mark_saved()
                return
            points = int(text)
            if points < 0:
                raise ValueError("Negative Punktzahl nicht erlaubt")
            sc.set_score(pid, 0, 1, (points, None), round_number=rnd)
            item.setText(str(points))
            self._update_simple_total(item.row())
            self._mark_saved()
        except (ValueError, Exception) as exc:
            show_error(self, exc)
            # restore
            self._simple_table.blockSignals(True)
            item.setText(text)
            self._simple_table.blockSignals(False)

    def _update_simple_total(self, row: int):
        mode = self._scoring_mode()
        num_rounds = self._num_rounds()
        if mode == "total_only":
            return  # total IS the cell
        total = 0
        for rn in range(num_rounds):
            it = self._simple_table.item(row, 4 + rn)
            if it and it.text().lstrip("-").isdigit():
                total += int(it.text())
        total_col = 4 + num_rounds
        tot_it = self._simple_table.item(row, total_col)
        if tot_it:
            self._simple_table.blockSignals(True)
            tot_it.setText(str(total))
            self._simple_table.blockSignals(False)

    def _mark_saved(self):
        bar = self.window().statusBar() if self.window() else None
        if bar is not None and hasattr(bar, "set_info"):
            bar.set_info(f"Zuletzt gespeichert: {datetime.now():%H:%M:%S}")

    def _move(self, index: QPersistentModelIndex, delta: int):
        def go():
            if self._stay is not None and self._stay.isValid():
                target = QModelIndex(self._stay)
                self._stay = None
            else:
                row = index.row() + delta
                while 0 <= row < self.model.rowCount() and self.mid.isRowHidden(row):
                    row += delta
                if not 0 <= row < self.model.rowCount():
                    return
                target = self.model.index(row, index.column())
            # focus first: the editor opened by setCurrentIndex must keep the keyboard focus
            self.mid.setFocus()
            self.mid.setCurrentIndex(target)
            self.mid.scrollTo(target)
        QTimer.singleShot(0, go)

    # ------------------------------------------------------------ filter
    def _apply_filter(self):
        cls = self.class_tabs.tabData(self.class_tabs.currentIndex()) \
            if self.class_tabs.count() else ALL
        group = self.group_filter.currentData() or ALL
        term = self.search.term().lower()
        for r in range(self.model.rowCount()):
            first = self.model.item(r, 0)
            hay = f"{first.text()} {self.model.item(r, 1).text()}".lower()
            complete = all(self.model.item(r, c).text() for c in self._score_columns())
            hidden = (cls != ALL and first.data(CLASS_ROLE) != cls) or \
                (group != ALL and first.data(GROUP_ROLE) != group) or \
                (bool(term) and term not in hay) or \
                (self.incomplete_only.isChecked() and complete)
            for v in (self.left, self.mid, self.right):
                v.setRowHidden(r, hidden)

    def _visible_rows(self):
        return [r for r in range(self.model.rowCount()) if not self.mid.isRowHidden(r)]

    # ------------------------------------------------------------ bulk + save
    def _header_menu(self, pos):
        if self.tournament is None or self.tournament.status == "closed":
            return
        col = self.mid.horizontalHeader().logicalIndexAt(pos)
        if col not in self._score_columns():
            return
        target, shot = self.cols[col - FIXED]
        label = f"Scheibe {target}" + (f", Schuss {shot}" if self.tournament.shots_per_target > 1
                                       else "")
        m = QMenu(self)
        sub = m.addMenu(f"{label} für alle auf … setzen")
        for z in self.zones:
            sub.addAction(zone_label(z)).triggered.connect(
                lambda _=False, zz=z, c=col, lb=label: self._fill_column(c, zz, lb))
        m.exec(self.mid.horizontalHeader().mapToGlobal(pos))

    def _fill_column(self, col: int, zone: dict, label: str):
        rows = self._visible_rows()
        existing = sum(bool(self.model.item(r, col).text()) for r in rows)
        text = f"{label} wird für {len(rows)} sichtbare Teilnehmer auf " \
               f"„{zone_label(zone)}“ gesetzt."
        if existing:
            text += f"\n\n{existing} vorhandene Werte werden überschrieben."
        if not ConfirmDialog.ask(self, "Werte für alle setzen?", text, "Setzen",
                                 destructive=bool(existing)):
            return
        with busy():
            for r in rows:
                pid, target, shot = self.model.item(r, col).data(CELL_ROLE)
                sc.set_score(pid, target, shot, (zone["points"], zone["zone"]),
                             round_number=self._current_round)
        self._mark_saved()
        Toast.show(self, f"{label}: {len(rows)} Werte gesetzt", Toast.SUCCESS)
        self.set_tournament(self.tournament)

    def save(self):
        """Cells are persisted on commit; this commits an open editor and confirms."""
        if self.tournament is None or self.tournament.status == "closed":
            return
        self.mid.setFocus()   # closes an open editor -> commit
        self._mark_saved()
        Toast.show(self, "Alle Eingaben sind gespeichert", Toast.SUCCESS)

    def show_incomplete(self):
        if self.class_tabs.count():
            self.class_tabs.setCurrentIndex(0)
        self.incomplete_only.setChecked(True)
        self._apply_filter()

    # global shortcuts
    def shortcut_save(self):
        self.save()

    def shortcut_find(self):
        self.search.setFocus()
        self.search.selectAll()
