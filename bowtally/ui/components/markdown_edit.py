# -*- coding: utf-8 -*-
"""Mehrzeiliges Textfeld mit Formatierungsleiste (fett, kursiv, durchgestrichen, Listen).

Drop-in für QPlainTextEdit: toPlainText() liefert den Text mit der Auszeichnung aus
services.markup, setPlainText() liest sie ein. Die Leiste sitzt im oberen Rand des Feldes.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QTextCharFormat, QTextCursor, QTextListFormat
from PySide6.QtWidgets import QHBoxLayout, QTextEdit, QToolButton, QWidget

from bowtally.services import markup

_LIST_STYLES = {"ul": QTextListFormat.Style.ListDisc, "ol": QTextListFormat.Style.ListDecimal}
TOOLBAR_H = 26


class MarkdownEdit(QTextEdit):
    def __init__(self, text: str = "", parent=None):
        super().__init__(parent)
        self.setTabChangesFocus(True)
        self._bar = QWidget(self)
        lay = QHBoxLayout(self._bar)
        lay.setContentsMargins(4, 2, 4, 0)
        lay.setSpacing(2)
        self._buttons = {}
        for key, label, tip, slot in (
                ("b", "F", "Fett (Strg+B)", lambda: self._toggle("b")),
                ("i", "K", "Kursiv (Strg+I)", lambda: self._toggle("i")),
                ("s", "S", "Durchgestrichen", lambda: self._toggle("s")),
                ("ul", "•", "Aufzählung", lambda: self._list("ul")),
                ("ol", "1.", "Nummerierung", lambda: self._list("ol"))):
            btn = QToolButton(objectName="iconButton", toolTip=tip, checkable=True)
            btn.setText(label)
            btn.setFixedSize(24, 22)
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            f = btn.font()
            f.setBold(key == "b")
            f.setItalic(key == "i")
            f.setStrikeOut(key == "s")
            btn.setFont(f)
            btn.clicked.connect(slot)
            lay.addWidget(btn)
            self._buttons[key] = btn
        lay.addStretch()
        self.setViewportMargins(0, TOOLBAR_H, 0, 0)
        self.cursorPositionChanged.connect(self._sync_buttons)
        self.currentCharFormatChanged.connect(self._sync_buttons)
        self.setPlainText(text)

    # ------------------------------------------------------------ value
    def setPlainText(self, text: str | None) -> None:       # noqa: N802 (Qt API)
        doc = self.document()
        doc.clear()
        cur = QTextCursor(doc)
        current_list = None
        for n, line in enumerate(markup.parse(text or "")):
            if n:
                cur.insertBlock()
            cur.setBlockFormat(cur.blockFormat().__class__())
            if line.kind == "p":
                current_list = None
            elif current_list is not None and current_list.format().style() == _LIST_STYLES[line.kind]:
                current_list.add(cur.block())
            else:
                current_list = cur.createList(_LIST_STYLES[line.kind])
            for span in line.spans:
                cur.insertText(span.text, _format(span))
        cur.movePosition(QTextCursor.MoveOperation.Start)
        self.setTextCursor(cur)
        doc.setModified(False)

    def toPlainText(self) -> str:       # noqa: N802 (Qt API)
        lines, count = [], 0
        block = self.document().firstBlock()
        while block.isValid():
            spans = []
            it = block.begin()
            while not it.atEnd():
                frag = it.fragment()
                fmt = frag.charFormat()
                for k, part in enumerate(frag.text().replace("￼", "").split(" ")):
                    if k:
                        spans.append(None)      # soft line break
                    span = markup.Span(part, fmt.font().bold(), fmt.fontItalic(), fmt.fontStrikeOut())
                    prev = spans[-1] if spans else None
                    if prev is not None and (prev.b, prev.i, prev.s) == (span.b, span.i, span.s):
                        spans[-1] = markup.Span(prev.text + part, span.b, span.i, span.s)
                    else:
                        spans.append(span)
                it += 1
            text_list = block.textList()
            style = text_list.format().style() if text_list else None
            count = count + 1 if style == _LIST_STYLES["ol"] else 0
            prefix = ("- " if style == _LIST_STYLES["ul"] else f"{count}. " if count else "")
            text = "".join("\n" if sp is None else markup.span_markup(sp) for sp in spans)
            lines.append(prefix + text if text.strip() else text)
            block = block.next()
        return "\n".join(lines)

    def setReadOnly(self, read_only: bool) -> None:       # noqa: N802 (Qt API)
        super().setReadOnly(read_only)
        self._bar.setVisible(not read_only)
        self.setViewportMargins(0, 0 if read_only else TOOLBAR_H, 0, 0)

    # ------------------------------------------------------------ toolbar
    def resizeEvent(self, e):
        super().resizeEvent(e)
        fw = self.frameWidth()
        self._bar.setGeometry(fw, fw, self.width() - 2 * fw, TOOLBAR_H)

    def keyPressEvent(self, e):
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier and e.key() in (Qt.Key.Key_B, Qt.Key.Key_I):
            self._toggle("b" if e.key() == Qt.Key.Key_B else "i")
            return
        super().keyPressEvent(e)

    def _toggle(self, key: str):
        fmt = QTextCharFormat()
        if key == "b":
            fmt.setFontWeight(QFont.Weight.Normal if self.fontWeight() >= QFont.Weight.Bold
                              else QFont.Weight.Bold)
        elif key == "i":
            fmt.setFontItalic(not self.fontItalic())
        else:
            fmt.setFontStrikeOut(not self.currentCharFormat().fontStrikeOut())
        self.mergeCurrentCharFormat(fmt)
        self._sync_buttons()

    def _list(self, kind: str):
        cur = self.textCursor()
        current = cur.currentList()
        if current is not None and current.format().style() == _LIST_STYLES[kind]:
            block_fmt = cur.blockFormat()
            block_fmt.setIndent(0)
            block_fmt.setObjectIndex(-1)
            cur.setBlockFormat(block_fmt)
        else:
            cur.createList(_LIST_STYLES[kind])
        self._sync_buttons()

    def _sync_buttons(self, *_):
        fmt = self.currentCharFormat()
        current = self.textCursor().currentList()
        style = current.format().style() if current else None
        for key, on in (("b", fmt.font().bold()), ("i", fmt.fontItalic()),
                        ("s", fmt.fontStrikeOut()), ("ul", style == _LIST_STYLES["ul"]),
                        ("ol", style == _LIST_STYLES["ol"])):
            self._buttons[key].setChecked(on)


def _format(span: markup.Span) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setFontWeight(QFont.Weight.Bold if span.b else QFont.Weight.Normal)
    fmt.setFontItalic(span.i)
    fmt.setFontStrikeOut(span.s)
    return fmt
