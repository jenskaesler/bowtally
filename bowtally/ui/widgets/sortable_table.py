# -*- coding: utf-8 -*-
"""Read-only table with column sorting and a full-text search field."""
from datetime import date

from PySide6.QtCore import QSortFilterProxyModel, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (QAbstractItemView, QHeaderView, QLineEdit, QTableView,
                               QVBoxLayout, QWidget)

ID_ROLE = Qt.ItemDataRole.UserRole + 1
SORT_ROLE = Qt.ItemDataRole.UserRole + 2
ROW_HEIGHT = 34


def display(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Ja" if value else "Nein"
    if isinstance(value, date):
        return value.strftime("%d.%m.%Y")
    return str(value)


class SortableTable(QWidget):
    activated = Signal(object)          # row id (double click / Enter)
    selectionChanged = Signal()

    def __init__(self, headers: list[str], searchable: bool = True,
                 multi_select: bool = False, parent=None):
        super().__init__(parent)
        self.model = QStandardItemModel(0, len(headers), self)
        self.model.setHorizontalHeaderLabels(headers)
        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)
        self.proxy.setSortRole(SORT_ROLE)
        self.proxy.setFilterKeyColumn(-1)
        self.proxy.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

        self.view = QTableView()
        self.view.setModel(self.proxy)
        # no initial sort column: keep the order delivered by the service
        self.view.horizontalHeader().setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
        self.view.setSortingEnabled(True)
        self.view.setAlternatingRowColors(True)
        self.view.verticalHeader().hide()
        self.view.verticalHeader().setDefaultSectionSize(ROW_HEIGHT)
        self.view.setShowGrid(False)
        self.view.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignLeft
                                                         | Qt.AlignmentFlag.AlignVCenter)
        self.view.horizontalHeader().setHighlightSections(False)
        self.view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.view.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection
                                   if multi_select
                                   else QAbstractItemView.SelectionMode.SingleSelection)
        self.view.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.view.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.view.horizontalHeader().setStretchLastSection(True)
        self.view.doubleClicked.connect(lambda idx: self.activated.emit(self._id_at(idx.row())))
        self.view.selectionModel().selectionChanged.connect(self.selectionChanged)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Suchen ...")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self.proxy.setFilterFixedString)
        self.search.setVisible(searchable)
        lay.addWidget(self.search)
        lay.addWidget(self.view)

    def set_rows(self, rows: list[list], ids: list) -> None:
        self.model.setRowCount(0)
        for row, row_id in zip(rows, ids):
            items = []
            for value in row:
                it = QStandardItem(display(value))
                it.setData(row_id, ID_ROLE)
                it.setData(float(value) if isinstance(value, (int, float))
                           and not isinstance(value, bool)
                           else value.isoformat() if isinstance(value, date)
                           else display(value).lower(), SORT_ROLE)
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    it.setTextAlignment(Qt.AlignmentFlag.AlignRight
                                        | Qt.AlignmentFlag.AlignVCenter)
                items.append(it)
            self.model.appendRow(items)
        if rows:   # numeric columns: right aligned header, like the values
            for c, value in enumerate(rows[0]):
                numeric = isinstance(value, (int, float)) and not isinstance(value, bool)
                self.model.setHeaderData(
                    c, Qt.Orientation.Horizontal,
                    (Qt.AlignmentFlag.AlignRight if numeric else Qt.AlignmentFlag.AlignLeft)
                    | Qt.AlignmentFlag.AlignVCenter, Qt.ItemDataRole.TextAlignmentRole)
        self.view.resizeColumnsToContents()

    def _id_at(self, proxy_row: int):
        return self.proxy.index(proxy_row, 0).data(ID_ROLE)

    def selected_ids(self) -> list:
        return [self._id_at(i.row()) for i in self.view.selectionModel().selectedRows()]

    def selected_id(self):
        ids = self.selected_ids()
        return ids[0] if ids else None

    def visible_rows(self) -> list[list[str]]:
        """Currently filtered rows in display order (for export of filtered data)."""
        return [[self.proxy.index(r, c).data() for c in range(self.proxy.columnCount())]
                for r in range(self.proxy.rowCount())]

    def visible_ids(self) -> list:
        return [self._id_at(r) for r in range(self.proxy.rowCount())]

    def headers(self) -> list[str]:
        return [self.model.headerData(c, Qt.Orientation.Horizontal)
                for c in range(self.model.columnCount())]
