# -*- coding: utf-8 -*-
"""Leichte Textauszeichnung der mehrzeiligen Felder (Markdown-Teilmenge, zeilenweise).

Inline: **fett**, *kursiv*, ~~durchgestrichen~~ (kombinierbar, z. B. ***fett kursiv***).
Zeilen: "- " Aufzählung, "1. " Nummerierung; jede Zeile bleibt eine Zeile. Texte ohne
Auszeichnung sind unverändert gültig, deshalb kann jedes vorhandene Feld so gelesen werden.
"""
import html
import re
from dataclasses import dataclass

_TOKEN = re.compile(r"(\*\*\*|\*\*|\*|~~)")
_LIST = re.compile(r"^(?:(-|\*) |(\d+)\. )(?=\S)")
_MARK = {"b": "**", "i": "*", "s": "~~"}


@dataclass(frozen=True)
class Span:
    text: str
    b: bool = False
    i: bool = False
    s: bool = False


@dataclass(frozen=True)
class Line:
    kind: str                  # "p" | "ul" | "ol"
    spans: tuple


def _closes_later(tokens: list[str], start: int, mark: str) -> bool:
    before = "".join(tokens[:start + 1])
    for j in range(start + 1, len(tokens)):
        if j % 2 and mark in tokens[j] and before and not before[-1].isspace():
            return True
        before += tokens[j]
    return False


def parse_inline(text: str) -> tuple:
    tokens = _TOKEN.split(text)
    state = {"b": False, "i": False, "s": False}
    spans = []

    def emit(s):
        if s:
            spans.append(Span(s, state["b"], state["i"], state["s"]))

    before = ""
    for idx, tok in enumerate(tokens):
        if idx % 2 == 0:
            emit(tok)
            before += tok
            continue
        after = "".join(tokens[idx + 1:])
        marks = ["s"] if tok == "~~" else ["b"] if tok == "**" else ["i"] if tok == "*" else ["b", "i"]
        literal = ""
        for key in marks:
            if state[key]:
                if before and not before[-1].isspace():      # a closing marker touches the text
                    state[key] = False
                else:
                    literal += _MARK[key]
            elif after and not after[0].isspace() and _closes_later(tokens, idx, _MARK[key]):
                state[key] = True
            else:
                literal += _MARK[key]
        emit(literal)
        before += tok
    return tuple(spans)


def parse(text: str | None) -> list[Line]:
    lines = []
    for raw in (text or "").replace("\r\n", "\n").split("\n"):
        m = _LIST.match(raw)
        kind = "p" if not m else "ol" if m.group(2) else "ul"
        lines.append(Line(kind, parse_inline(raw[m.end():] if m else raw)))
    return lines


def unlist(text: str) -> str:
    """Line without its list marker (for texts that are set as list items anyway)."""
    return _LIST.sub("", text)


def span_markup(span: Span) -> str:
    """One span back to markup; whitespace at the edges stays outside the markers."""
    if not span.text.strip() or not (span.b or span.i or span.s):
        return span.text
    lead = span.text[:len(span.text) - len(span.text.lstrip())]
    core = span.text.strip()
    trail = span.text[len(span.text.rstrip()):]
    open_ = ("**" if span.b else "") + ("*" if span.i else "") + ("~~" if span.s else "")
    close = ("~~" if span.s else "") + ("*" if span.i else "") + ("**" if span.b else "")
    return f"{lead}{open_}{core}{close}{trail}"


def _render(text, tags: dict, bullet: str, number, joiner: str) -> str:
    out, count = [], 0
    for line in parse(text):
        body = "".join(
            (tags["b"][0] if sp.b else "") + (tags["i"][0] if sp.i else "")
            + (tags["s"][0] if sp.s else "") + tags["esc"](sp.text)
            + (tags["s"][1] if sp.s else "") + (tags["i"][1] if sp.i else "")
            + (tags["b"][1] if sp.b else "") for sp in line.spans)
        count = count + 1 if line.kind == "ol" else 0
        if line.kind == "ul":
            body = bullet + body
        elif line.kind == "ol":
            body = number(count) + body
        out.append(body)
    return joiner.join(out)


def to_html(text: str | None) -> str:
    """Inline HTML with <br> between lines (e-mail, QLabel)."""
    return _render(text, {"b": ("<b>", "</b>"), "i": ("<i>", "</i>"), "s": ("<s>", "</s>"),
                          "esc": html.escape}, "&bull; ", lambda n: f"{n}. ", "<br>")


def to_reportlab(text: str | None) -> str:
    """Paragraph markup of reportlab (<b>, <i>, <strike>), lines separated by <br/>."""
    esc = lambda s: s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return _render(text, {"b": ("<b>", "</b>"), "i": ("<i>", "</i>"),
                          "s": ("<strike>", "</strike>"), "esc": esc},
                   "• ", lambda n: f"{n}. ", "<br/>")


def to_whatsapp(text: str | None) -> str:
    """WhatsApp's own markers: *fett*, _kursiv_, ~durchgestrichen~."""
    return _render(text, {"b": ("*", "*"), "i": ("_", "_"), "s": ("~", "~"), "esc": str},
                   "• ", lambda n: f"{n}. ", "\n")


def to_plain(text: str | None) -> str:
    return _render(text, {"b": ("", ""), "i": ("", ""), "s": ("", ""), "esc": str},
                   "• ", lambda n: f"{n}. ", "\n")
