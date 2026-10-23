# -*- coding: utf-8 -*-
"""Base class for list pages: context header with search, data table with empty state,
action bar for the selection and an optional side drawer for create/edit."""
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QHBoxLayout, QMenu, QVBoxLayout, QWidget

from bowtally.ui.components.action_bar import ActionBar
from bowtally.ui.components.data_table import DataTable
from bowtally.ui.components.drawer import SideDrawer
from bowtally.ui.components.empty_state import EmptyState
from bowtally.ui.components.form_field import Form
from bowtally.ui.components.page_header import PageHeader
from bowtally.ui.components.search_bar import SearchBar


def menu(parent, entries) -> QMenu:
    """entries: (text, callback, enabled) or None for a separator."""
    m = QMenu(parent)
    for e in entries:
        if e is None:
            m.addSeparator()
            continue
        text, callback, enabled = (list(e) + [True])[:3]
        act = QAction(text, m)
        act.setEnabled(enabled)
        act.triggered.connect(callback)
        m.addAction(act)
    return m


class ListView(QWidget):
    def __init__(self, title: str, headers: list[str], empty: EmptyState,
                 form: Form | None = None, search_placeholder: str = "Suchen …",
                 multi_select: bool = False, sortable: bool = True, reorderable: bool = False,
                 parent=None):
        super().__init__(parent)
        self.header = PageHeader(title)
        self.search = SearchBar(search_placeholder)
        self.search.searchChanged.connect(lambda term: self.table.apply_filter(term))
        self.header.add(self.search)
        self.table = DataTable(headers, empty, multi_select, sortable, reorderable)
        self.table.selectionChanged.connect(self.on_selection)
        self.table.contextMenuRequested.connect(self._context_menu)
        self.action_bar = ActionBar()
        self.drawer = SideDrawer(form) if form is not None else None
        if self.drawer is not None:
            self.drawer.saveRequested.connect(self.save_form)

        main = QVBoxLayout()
        main.setContentsMargins(0, 0, 0, 0)
        main.setSpacing(10)
        main.addWidget(self.header)
        main.addWidget(self.table, 1)
        main.addWidget(self.action_bar)
        self.main_layout = main
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(16)
        lay.addLayout(main, 1)
        if self.drawer is not None:
            lay.addWidget(self.drawer)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh()

    # ------------------------------------------------------------ to override
    def refresh(self) -> None:
        raise NotImplementedError

    def on_selection(self, ids: list) -> None:
        self.action_bar.set_actions("", [])

    def context_entries(self, row_id) -> list:
        return []

    def new_item(self) -> None:
        pass

    def save_form(self) -> None:
        pass

    # ------------------------------------------------------------ shared behavior
    def _context_menu(self, row_id, pos):
        entries = self.context_entries(row_id)
        if entries:
            menu(self, entries).exec(pos)

    def selection_info(self, n: int, singular: str, plural: str) -> str:
        return f"1 {singular} ausgewählt" if n == 1 else f"{n} {plural} ausgewählt"

    # global shortcuts (dispatched by the main window)
    def shortcut_new(self):
        self.new_item()

    def shortcut_find(self):
        self.search.setFocus()
        self.search.selectAll()

    def shortcut_save(self):
        if self.drawer is not None and self.drawer.is_open():
            self.save_form()

    def close_drawer(self) -> bool:
        return self.drawer is None or self.drawer.request_close()
