# -*- coding: utf-8 -*-
"""QTableWidget wrapper: sorting, text filter, empty state, selection callbacks,
optional inline editing, drag-and-drop row ordering and configurable columns."""
import json
from dataclasses import dataclass
from datetime import date
from typing import Callable

from PySide6.QtCore import QPoint, QSettings, Qt, Signal
from PySide6.QtGui import QAction, QBrush, QColor, QIcon
from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QHeaderView, QMenu,
                               QStackedLayout, QStyledItemDelegate, QTableWidget,
                               QTableWidgetItem, QWidget)

from bowtally.ui import theme as _theme

from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.status_chip import CHIP_ROLE, ChipDelegate

ID_ROLE = Qt.ItemDataRole.UserRole + 1
SORT_ROLE = Qt.ItemDataRole.UserRole + 2
VALUE_ROLE = Qt.ItemDataRole.UserRole + 3     # raw value behind a combo cell (e.g. an id)
ROW_HEIGHT = 34
COLUMNS_GROUP = "TableColumns"     # QSettings group: one key per table, a pure UI setting


@dataclass(frozen=True)
class Column:
    """Column of a configurable table. Default columns (hideable=False) are always shown;
    optional ones are hidden until the user switches them on in the header menu."""
    key: str
    label: str
    hideable: bool = False
    default_visible: bool = True


def optional(key: str, label: str) -> Column:
    """An existing data field that is not shown by default."""
    return Column(key, label, hideable=True, default_visible=False)


def optional_columns(spec) -> list[Column]:
    """spec: [(Column, getter)] of a view's optional fields."""
    return [col for col, _get in spec]


def optional_values(spec, obj) -> list:
    return [get(obj) for _col, get in spec]


def _as_columns(headers) -> list[Column]:
    return [h if isinstance(h, Column) else Column(h, h) for h in headers]


def display(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Ja" if value else "Nein"
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    return str(value)


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


@dataclass
class Cell:
    """Rich cell. Plain values in a row are wrapped automatically."""
    value: object = None
    text: str | None = None          # display text, default display(value)
    sort: object = None              # sort key, default derived from value
    chip: tuple | None = None        # (text, kind) -> painted as status pill
    bold: bool = False
    background: str | None = None    # color
    foreground: str | None = None    # text color
    tooltip: str = ""
    editable: bool = False
    data: object = None              # VALUE_ROLE


class _SortItem(QTableWidgetItem):
    def __lt__(self, other):
        a, b = self.data(SORT_ROLE), other.data(SORT_ROLE)
        if type(a) is not type(b):   # mixed (e.g. number vs. empty) -> compare as text
            return str(a) < str(b)
        try:
            return a < b
        except TypeError:
            return str(a) < str(b)


class ReorderTable(QTableWidget):
    """Emits rowsDropped instead of moving items; the owner reorders its data."""
    rowsDropped = Signal(list, int)   # source rows, target row

    def dropEvent(self, event):
        # Rows are not moved by Qt (it would overwrite cells); the owner reorders the data.
        if event.source() is self:
            target = self.indexAt(event.position().toPoint()).row()
            rows = sorted({i.row() for i in self.selectedIndexes()})
            event.setDropAction(Qt.DropAction.IgnoreAction)
            event.accept()
            self.rowsDropped.emit(rows, self.rowCount() if target < 0 else target)


class ComboDelegate(QStyledItemDelegate):
    """Inline dropdown. options() -> [(text, data)]; editable allows free text."""

    def __init__(self, options: Callable[[], list], editable: bool = False, parent=None):
        super().__init__(parent)
        self.options, self.editable = options, editable

    def createEditor(self, parent, option, index):
        cb = QComboBox(parent)
        cb.setEditable(self.editable)
        for text, data in self.options():
            cb.addItem(text, data)
        return cb

    def setEditorData(self, editor: QComboBox, index):
        idx = editor.findData(index.data(VALUE_ROLE))
        if idx < 0:
            idx = editor.findText(index.data() or "")
        if idx >= 0:
            editor.setCurrentIndex(idx)
        elif self.editable:
            editor.setEditText(index.data() or "")
        if not self.editable:
            editor.showPopup()

    def setModelData(self, editor: QComboBox, model, index):
        text = editor.currentText().strip()
        data = editor.currentData() if editor.findText(text) >= 0 else None
        model.setData(index, data if data is not None else text, VALUE_ROLE)
        model.setData(index, text, Qt.ItemDataRole.DisplayRole)


class TimeDelegate(QStyledItemDelegate):
    """Inline time entry in the mask __:__; a blank time is stored as NULL."""

    def createEditor(self, parent, option, index):
        from bowtally.ui.components.form_field import TimeField
        return TimeField(parent)

    def setEditorData(self, editor, index):
        editor.set_field_value(index.data(Qt.ItemDataRole.DisplayRole) or None)

    def setModelData(self, editor, model, index):
        if editor.input_error():
            return                              # incomplete time: keep the stored value
        s = editor.field_value()
        model.setData(index, s, VALUE_ROLE)
        model.setData(index, s or "", Qt.ItemDataRole.DisplayRole)


class DataTable(QWidget):
    selectionChanged = Signal(list)              # selected ids
    activated = Signal(object)                   # id (double click / Enter)
    contextMenuRequested = Signal(object, QPoint)   # id, global position
    cellEdited = Signal(object, int, object)     # id, column, value (VALUE_ROLE or text)
    reordered = Signal(list)                     # all ids in new order

    def __init__(self, headers: list, empty: EmptyState | None = None,
                 multi_select: bool = False, sortable: bool = True, reorderable: bool = False,
                 parent=None, table_key: str | None = None):
        """headers: labels or Column objects. With `table_key` the user can show optional
        columns (header right-click) and move columns; both are kept in QSettings."""
        super().__init__(parent)
        self.columns = _as_columns(headers)
        headers = self.headers = [c.label for c in self.columns]
        self.table_key = table_key
        self.empty = empty
        self._loading = False
        self._last_edit = None
        self._term = ""
        self._col0 = 1 if reorderable else 0
        t = self.table = ReorderTable(0, len(headers) + self._col0)
        t.setHorizontalHeaderLabels(([""] if self._col0 else []) + list(headers))
        t.verticalHeader().hide()
        t.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        t.setShowGrid(False)
        t.setAlternatingRowColors(True)
        t.setWordWrap(False)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection if multi_select
                           else QAbstractItemView.SelectionMode.SingleSelection)
        t.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked
                          | QAbstractItemView.EditTrigger.EditKeyPressed)
        header = t.horizontalHeader()
        header.setHighlightSections(False)
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        header.setStretchLastSection(True)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # no initial sort column: keep the order delivered by the service until the user sorts
        header.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self._sortable = sortable and not reorderable
        if reorderable:
            h = t.horizontalHeader()
            h.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            t.setColumnWidth(0, 28)
            t.setDragEnabled(True)
            t.setAcceptDrops(True)
            t.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
            t.setDropIndicatorShown(True)
            t.setDragDropOverwriteMode(False)
            t.rowsDropped.connect(self._on_rows_dropped)
        self._chips = ChipDelegate(t)
        t.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        t.customContextMenuRequested.connect(self._on_context_menu)
        t.itemSelectionChanged.connect(lambda: self.selectionChanged.emit(self.selected_ids()))
        t.itemDoubleClicked.connect(self._on_double_click)
        t.itemChanged.connect(self._on_item_changed)

        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.addWidget(t)
        if empty is not None:
            self._stack.addWidget(empty)
        if table_key:
            header.setSectionsMovable(True)
            header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            header.customContextMenuRequested.connect(self._header_menu)
            header.sectionMoved.connect(self._on_section_moved)
            self._apply_column_state()

    # ------------------------------------------------------------ content
    def set_headers(self, headers: list) -> None:
        """New column set (e.g. per scoring rule); the saved column state is applied again."""
        if self.table_key:
            self._reset_column_order()
        self.columns = _as_columns(headers)
        headers = self.headers = [c.label for c in self.columns]
        self.table.setColumnCount(len(headers) + self._col0)
        self.table.setHorizontalHeaderLabels(([""] if self._col0 else []) + list(headers))
        if self.table_key:
            self._apply_column_state()

    # ------------------------------------------------------------ configurable columns
    def _settings_key(self) -> str:
        return f"{COLUMNS_GROUP}/{self.table_key}"

    def _load_state(self) -> tuple[set[str], list[str]]:
        s = QSettings("BowTally", "BowTally")
        key = self._settings_key()
        try:
            visible = json.loads(s.value(f"{key}/visible_optional", "null"))
            order = json.loads(s.value(f"{key}/order", "[]"))
        except (TypeError, ValueError):       # damaged entry: back to the defaults
            visible, order = None, []
        if not isinstance(visible, list):
            visible = [c.key for c in self.columns if c.hideable and c.default_visible]
        if not isinstance(order, list):
            order = []
        return set(visible), [k for k in order if isinstance(k, str)]

    def _save_state(self) -> None:
        h = self.table.horizontalHeader()
        logical = sorted(range(self._col0, self.table.columnCount()), key=h.visualIndex)
        s = QSettings("BowTally", "BowTally")
        key = self._settings_key()
        s.setValue(f"{key}/visible_optional", json.dumps(
            [c.key for i, c in enumerate(self.columns)
             if c.hideable and not self.table.isColumnHidden(i + self._col0)]))
        s.setValue(f"{key}/order", json.dumps([self.columns[i - self._col0].key for i in logical]))

    def _reset_column_order(self) -> None:
        h = self.table.horizontalHeader()
        h.blockSignals(True)
        for logical in range(self.table.columnCount()):
            h.moveSection(h.visualIndex(logical), logical)
        h.blockSignals(False)

    def _apply_column_state(self) -> None:
        visible, order = self._load_state()
        keys = [c.key for c in self.columns]
        for i, c in enumerate(self.columns):
            self.table.setColumnHidden(i + self._col0, c.hideable and c.key not in visible)
        # saved order first; columns unknown to it (new ones) follow in schema order
        wanted = [k for k in order if k in keys] + [k for k in keys if k not in order]
        h = self.table.horizontalHeader()
        h.blockSignals(True)
        for pos, k in enumerate(wanted):
            h.moveSection(h.visualIndex(keys.index(k) + self._col0), pos + self._col0)
        h.blockSignals(False)

    def _on_section_moved(self, _logical: int, _old: int, _new: int) -> None:
        h = self.table.horizontalHeader()
        if self._col0 and h.visualIndex(0) != 0:      # the drag grip stays the first column
            h.blockSignals(True)
            h.moveSection(h.visualIndex(0), 0)
            h.blockSignals(False)
        self._save_state()

    def column_menu(self) -> QMenu:
        """Checkbox list of all columns; default columns are checked and locked."""
        m = QMenu(self)
        m.setToolTipsVisible(True)
        h = self.table.horizontalHeader()
        for i in sorted(range(len(self.columns)), key=lambda i: h.visualIndex(i + self._col0)):
            c = self.columns[i]
            act = QAction(c.label, m)
            act.setCheckable(True)
            act.setChecked(not self.table.isColumnHidden(i + self._col0))
            act.setEnabled(c.hideable)
            if not c.hideable:
                act.setToolTip("Standardspalte, immer sichtbar")
            act.toggled.connect(lambda on, col=i + self._col0: self._set_column_visible(col, on))
            m.addAction(act)
        return m

    def _header_menu(self, pos: QPoint) -> None:
        self.column_menu().exec(self.table.horizontalHeader().mapToGlobal(pos))

    def _set_column_visible(self, column: int, visible: bool) -> None:
        self.table.setColumnHidden(column, not visible)
        if visible:
            self.table.resizeColumnToContents(column)
        self._save_state()

    def set_rows(self, rows: list[list], ids: list) -> None:
        t = self.table
        selected = set(self.selected_ids())
        self._loading = True
        self._last_edit = None
        t.setSortingEnabled(False)
        t.clearContents()
        t.setRowCount(len(rows))
        muted = _theme.current()["text2"]
        for r, (row, row_id) in enumerate(zip(rows, ids)):
            if self._col0:
                grip = QTableWidgetItem()
                grip.setIcon(QIcon(_theme.pixmap("grip", muted, 16)))
                grip.setToolTip("Ziehen, um die Reihenfolge zu ändern")
                grip.setData(ID_ROLE, row_id)
                grip.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
                              | Qt.ItemFlag.ItemIsDragEnabled)
                t.setItem(r, 0, grip)
            for c, value in enumerate(row):
                cell = value if isinstance(value, Cell) else Cell(value)
                t.setItem(r, c + self._col0, self._make_item(cell, row_id))
        for c in range(len(self.headers)):
            if any(isinstance(row[c], Cell) and row[c].chip for row in rows):
                t.setItemDelegateForColumn(c + self._col0, self._chips)
        t.setSortingEnabled(self._sortable)
        self._loading = False
        t.resizeColumnsToContents()
        for c in range(self._col0, t.columnCount()):
            t.setColumnWidth(c, min(max(t.columnWidth(c) + 16, 70), 360))
        for c in range(len(self.headers)):   # chips are wider than their plain text
            chips = [row[c].chip for row in rows if isinstance(row[c], Cell) and row[c].chip]
            if chips:
                fm = t.fontMetrics()
                t.setColumnWidth(c + self._col0,
                                 max(fm.horizontalAdvance(f"●  {text}") for text, _k in chips)
                                 + 48)
        self.select_ids(selected)
        self.apply_filter(self._term)

    def _make_item(self, cell: Cell, row_id) -> QTableWidgetItem:
        item = _SortItem(cell.text if cell.text is not None else
                         (cell.chip[0] if cell.chip else display(cell.value)))
        item.setData(ID_ROLE, row_id)
        raw = cell.value
        sort = cell.sort if cell.sort is not None else (
            float(raw) if _is_number(raw) else raw.isoformat() if isinstance(raw, date)
            else item.text().lower())
        item.setData(SORT_ROLE, sort)
        if cell.chip:
            item.setData(CHIP_ROLE, cell.chip)
        if cell.data is not None:
            item.setData(VALUE_ROLE, cell.data)
        if item.text().endswith("€"):      # only currency is right aligned; headers stay left
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if cell.bold:
            f = item.font()
            f.setBold(True)
            item.setFont(f)
        if cell.background:
            item.setBackground(QBrush(QColor(cell.background)))
        if cell.foreground:
            item.setForeground(QBrush(QColor(cell.foreground)))
        if cell.tooltip:
            item.setToolTip(cell.tooltip)
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable \
            | Qt.ItemFlag.ItemIsDragEnabled
        if cell.editable:
            flags |= Qt.ItemFlag.ItemIsEditable
        item.setFlags(flags)
        return item

    def set_delegate(self, column: int, delegate) -> None:
        self.table.setItemDelegateForColumn(column, delegate)

    def row_count(self) -> int:
        return self.table.rowCount()

    # ------------------------------------------------------------ filter / empty state
    def apply_filter(self, term: str) -> None:
        self._term = term = (term or "").strip()
        needle = term.lower()
        t = self.table
        visible = 0
        for r in range(t.rowCount()):
            hay = " ".join((t.item(r, c).text() if t.item(r, c) else "")
                           for c in range(t.columnCount()) if not t.isColumnHidden(c)).lower()
            hidden = bool(needle) and needle not in hay
            t.setRowHidden(r, hidden)
            visible += not hidden
        if self.empty is None:
            return
        if t.rowCount() == 0:
            self.empty.show_empty()
            self._stack.setCurrentWidget(self.empty)
        elif visible == 0:
            self.empty.show_no_results(term)
            self._stack.setCurrentWidget(self.empty)
        else:
            self._stack.setCurrentWidget(t)

    # ------------------------------------------------------------ selection
    def _row_id(self, row: int):
        item = self.table.item(row, 0)
        return item.data(ID_ROLE) if item else None

    def selected_ids(self) -> list:
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self._row_id(r) for r in rows]

    def selected_id(self):
        ids = self.selected_ids()
        return ids[0] if ids else None

    def select_ids(self, ids) -> None:
        ids = set(ids or [])
        t = self.table
        t.clearSelection()
        for r in range(t.rowCount()):
            if self._row_id(r) in ids:
                t.selectRow(r)

    def visible_ids(self) -> list:
        return [self._row_id(r) for r in range(self.table.rowCount())
                if not self.table.isRowHidden(r)]

    def visible_rows(self) -> list[list[str]]:
        """Filtered rows in display order (exports)."""
        t = self.table
        return [[t.item(r, c).text() if t.item(r, c) else ""
                 for c in range(self._col0, t.columnCount())]
                for r in range(t.rowCount()) if not t.isRowHidden(r)]

    def all_rows(self) -> list[list[str]]:
        t = self.table
        return [[t.item(r, c).text() if t.item(r, c) else ""
                 for c in range(self._col0, t.columnCount())]
                for r in range(t.rowCount())]

    def is_filtered(self) -> bool:
        return bool(self._term)

    # ------------------------------------------------------------ events
    def _on_double_click(self, item: QTableWidgetItem):
        if not (item.flags() & Qt.ItemFlag.ItemIsEditable):
            self.activated.emit(item.data(ID_ROLE))

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter) and self.selected_id() is not None \
                and self.table.state() != QAbstractItemView.State.EditingState:
            self.activated.emit(self.selected_id())
            return
        super().keyPressEvent(event)

    def _on_context_menu(self, pos: QPoint):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row_id = self._row_id(index.row())
        if row_id not in self.selected_ids():
            self.table.selectRow(index.row())
        self.contextMenuRequested.emit(row_id, self.table.viewport().mapToGlobal(pos))

    def _on_item_changed(self, item: QTableWidgetItem):
        if self._loading:
            return
        col = item.column() - self._col0
        if col < 0:
            return
        value = item.data(VALUE_ROLE)
        edit = (item.data(ID_ROLE), col, value if value is not None else item.text())
        if edit == self._last_edit:     # a combo sets value + text -> two change events
            return
        self._last_edit = edit
        self.cellEdited.emit(*edit)

    def _on_rows_dropped(self, rows: list[int], target: int):
        ids = [self._row_id(r) for r in range(self.table.rowCount())]
        moving = [ids[r] for r in rows]
        rest = [i for i in ids if i not in moving]
        insert_at = len([i for i in ids[:target] if i not in moving])
        new_order = rest[:insert_at] + moving + rest[insert_at:]
        if new_order != ids:
            self._rearrange_rows(new_order, ids)
            self.reordered.emit(new_order)

    def _rearrange_rows(self, new_order: list, old_order: list):
        t = self.table
        ncols = t.columnCount()
        id_items = {id_: [t.item(r, c).clone() if t.item(r, c) else None
                          for c in range(ncols)]
                    for r, id_ in enumerate(old_order)}
        self._loading = True
        for new_r, id_ in enumerate(new_order):
            for c, item in enumerate(id_items.get(id_, [None] * ncols)):
                t.setItem(new_r, c, item)
        self._loading = False
