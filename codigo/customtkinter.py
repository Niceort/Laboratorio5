import tkinter as tk
from tkinter import ttk


class ThemeManager:
    appearance_mode = "system"
    color_theme = "blue"


def set_appearance_mode(mode: str) -> None:
    ThemeManager.appearance_mode = mode


def set_default_color_theme(theme: str) -> None:
    ThemeManager.color_theme = theme


class CTk(tk.Tk):
    pass


class CTkFrame(tk.Frame):
    def __init__(self, master=None, fg_color=None, corner_radius=None, **kwargs):
        super().__init__(master, **kwargs)
        if fg_color is not None:
            self.configure(bg=fg_color)


class CTkScrollableFrame(CTkFrame):
    def __init__(self, master=None, **kwargs):
        super().__init__(master, **kwargs)
        self._canvas = tk.Canvas(self, highlightthickness=0)
        self._scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._content = tk.Frame(self._canvas)
        self._content.bind("<Configure>", self._on_configure)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._canvas.create_window((0, 0), window=self._content, anchor="nw")
        self._canvas.pack(side="left", fill="both", expand=True)
        self._scrollbar.pack(side="right", fill="y")

    def _on_configure(self, _event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def __getattr__(self, item):
        return getattr(self._content, item)


class CTkLabel(tk.Label):
    def __init__(self, master=None, text_font=None, font=None, **kwargs):
        if text_font is not None and font is None:
            kwargs["font"] = text_font
        elif font is not None:
            kwargs["font"] = font
        super().__init__(master, **kwargs)


class CTkButton(tk.Button):
    pass


class CTkEntry(tk.Entry):
    pass


class CTkTextbox(tk.Text):
    def insert(self, index, chars, *args):
        super().insert(index, chars, *args)


class CTkTabview(ttk.Notebook):
    def add(self, name):
        frame = tk.Frame(self)
        super().add(frame, text=name)
        return frame

    def tab(self, name):
        tabs = self.tabs()
        for tab_id in tabs:
            if self.tab(tab_id, "text") == name:
                return self.nametowidget(tab_id)
        raise KeyError(name)


class CTkOptionMenu(tk.OptionMenu):
    def __init__(self, master, variable, *values, command=None, **kwargs):
        self._command = command
        self._variable = variable
        super().__init__(master, variable, *values, command=self._on_select)
        if kwargs:
            self.configure(**kwargs)

    def _on_select(self, value):
        if self._command is not None:
            self._command(value)


class CTkFont:
    def __init__(self, size=12, weight="normal"):
        self.spec = ("Arial", size, weight)

    def __iter__(self):
        return iter(self.spec)

    def __str__(self):
        return "Arial {0} {1}".format(self.spec[1], self.spec[2])
