# -*- coding: utf-8 -*-
"""
tab_base.py — Klasa bazowa dla zakładek UI.

Eliminuje powtarzający się kod delegatów w każdej zakładce.
Każda klasa Tab dziedziczy z TabBase i automatycznie uzyskuje
dostęp do helperów UI przez self.app.
"""

import tkinter as tk
from constants import CREAM


class TabBase(tk.Frame):
    """Klasa bazowa dla zakładek — deleguje helpery UI do self.app."""

    def __init__(self, master, app):
        super().__init__(master, bg=CREAM)
        self.app = app

    def _card(self, parent, title=None, pady=8):
        return self.app._card(parent, title, pady)

    def _lbl(self, parent, text, col=0, row=0, sticky="w", span=1):
        self.app._lbl(parent, text, col, row, sticky, span)

    def _entry(self, parent, row=0, col=1, width=18, span=1, textvariable=None):
        return self.app._entry(parent, row, col, width, span, textvariable)

    def _combo(self, parent, values, row=0, col=1, width=20):
        return self.app._combo(parent, values, row, col, width)

    def _btn(self, parent, text, cmd, gold=False):
        return self.app._btn(parent, text, cmd, gold)

    def _res_row(self, parent, label, value, color=None, big=False):
        self.app._res_row(parent, label, value, color, big)

    def _clear_frame(self, frame):
        self.app._clear_frame(frame)

    def _scrollable(self, parent):
        return self.app._scrollable(parent)
