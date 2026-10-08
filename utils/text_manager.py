"""Manage an ordered text library while preserving the exact editable content."""
import copy
import tkinter as tk
from tkinter import ttk, messagebox
import unicodedata

from .io_utils import TEXT_FILE_NAME, get__file_path, save_texts

SUGGESTED_CHARACTER_GOAL = 400


def visible_whitespace(text: str) -> str:
    """A display-only representation; these markers never enter the saved text."""
    output = []
    for char in text:
        if char == " ":
            output.append("·")
        elif char == "\n":
            output.append("↵\n")
        elif char == "\t":
            output.append("⇥")
        elif char.isspace() or unicodedata.category(char) in ("Cc", "Cf"):
            output.append(f"⟦U+{ord(char):04X} {unicodedata.name(char, 'CONTROL')}⟧")
        else:
            output.append(char)
    return "".join(output)


class TextManager:
    def __init__(self, app, parent=None):
        self.app = app
        self.entries = copy.deepcopy(app.text_entries)
        self.saved_entries = copy.deepcopy(self.entries)
        self.index = None
        self.drag_index = None
        self.loading = False
        self.embedded = parent is not None
        if self.embedded:
            self.window = ttk.Frame(parent)
            self.window.pack(fill="both", expand=True)
        else:
            self.window = tk.Toplevel(app.master)
            self.window.title("Manage texts")
            self.window.geometry("950x650")
            self.window.minsize(700, 450)
            self.window.transient(app.master)
            self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.columnconfigure(1, weight=1)
        self.window.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(self.window, padding=10)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.rowconfigure(1, weight=1)
        sidebar.columnconfigure(0, weight=1)
        ttk.Label(sidebar, text="Texts (drag to reorder)").grid(row=0, column=0, sticky="w")
        self.listbox = tk.Listbox(sidebar, width=27, exportselection=False, font=app.ui_font)
        self.listbox.grid(row=1, column=0, sticky="nsew", pady=8)
        list_scroll = ttk.Scrollbar(sidebar, orient="vertical", command=self.listbox.yview)
        list_scroll.grid(row=1, column=1, sticky="ns", pady=8)
        self.listbox.configure(yscrollcommand=list_scroll.set)
        self.listbox.bind("<<ListboxSelect>>", self.select)
        self.listbox.bind("<ButtonPress-1>", self.start_drag, add="+")
        self.listbox.bind("<B1-Motion>", self.drag)
        self.listbox.bind("<ButtonRelease-1>", self.end_drag, add="+")
        actions = ttk.Frame(sidebar)
        actions.grid(row=2, column=0, sticky="ew")
        for i, (label, command) in enumerate((("Add", self.add), ("Delete", self.delete),
                                              ("Move up", lambda: self.move(-1)),
                                              ("Move down", lambda: self.move(1)))):
            ttk.Button(actions, text=label, command=command).grid(row=i // 2, column=i % 2, sticky="ew", padx=2, pady=2)

        editor = ttk.Frame(self.window, padding=10)
        editor.grid(row=0, column=1, sticky="nsew")
        editor.columnconfigure(0, weight=1)
        editor.rowconfigure(3, weight=2)
        editor.rowconfigure(5, weight=1)
        ttk.Label(editor, text="Text name").grid(row=0, column=0, sticky="w")
        self.name_var = tk.StringVar(self.window)
        self.name_entry = ttk.Entry(editor, textvariable=self.name_var, font=app.ui_font)
        self.name_entry.grid(row=1, column=0, sticky="ew", pady=(4, 10))
        self.name_var.trace_add("write", self.name_changed)
        ttk.Label(editor, text="Edit text (wraps automatically; Enter adds a real newline)", wraplength=430).grid(row=2, column=0, sticky="w")
        self.body = self.make_text(editor, 3, editable=True)
        self.body.bind("<<Modified>>", self.body_changed)
        ttk.Label(editor, text="Whitespace preview: · space   ⇥ tab   ↵ newline   ⟦…⟧ other invisible characters", wraplength=430).grid(row=4, column=0, sticky="w", pady=(10, 4))
        self.preview = self.make_text(editor, 5, editable=False)
        self.count_var = tk.StringVar(self.window)
        ttk.Label(editor, textvariable=self.count_var, wraplength=430).grid(row=6, column=0, sticky="w", pady=4)
        footer = ttk.Frame(self.window, padding=10)
        footer.grid(row=1, column=0, columnspan=2, sticky="ew")
        self.status_var = tk.StringVar(self.window, value="Changes are saved only when you click Save changes.")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, wraplength=450).grid(row=0, column=0, sticky="w", padx=(0, 8))
        ttk.Button(footer, text="Discard changes" if self.embedded else "Close",
                   command=self.discard if self.embedded else self.close).grid(row=0, column=2, padx=4)
        ttk.Button(footer, text="Save changes", command=self.save).grid(row=0, column=1, padx=4)
        self.refresh_list()
        self.show_entry(0 if self.entries else None)
        # ttk shares the app styles; classic Tk widgets need explicit colors.
        from .ui_utils import DARK_THEME, LIGHT_THEME
        self.apply_theme(DARK_THEME if app.dark_mode_enabled else LIGHT_THEME)

    def make_text(self, parent, row, editable):
        frame = ttk.Frame(parent)
        frame.grid(row=row, column=0, sticky="nsew")
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        widget = tk.Text(frame, wrap="word", height=6, undo=editable, font=self.app.text_font)
        widget.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(frame, command=widget.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        widget.configure(yscrollcommand=vertical.set)
        if not editable:
            widget.configure(state="disabled")
        return widget

    def apply_theme(self, theme):
        if not self.embedded:
            self.window.configure(bg=theme["background"])
        for widget in (self.body, self.preview):
            widget.configure(bg=theme["input_background"], fg=theme["text"],
                             insertbackground=theme["text"], selectbackground=theme["select_background"],
                             selectforeground=theme["select_foreground"], highlightbackground=theme["border"])
        self.listbox.configure(bg=theme["surface"], fg=theme["text"],
                               selectbackground=theme["select_background"], selectforeground=theme["select_foreground"])
        if not self.embedded:
            self.app._set_native_title_bar_theme(self.window, self.app.dark_mode_enabled, theme)

    def commit_editor(self):
        if self.index is not None:
            self.entries[self.index] = {"name": self.name_var.get(), "text": self.body.get("1.0", "end-1c")}

    def refresh_list(self):
        self.listbox.delete(0, tk.END)
        for i, entry in enumerate(self.entries, 1):
            self.listbox.insert(tk.END, f"{i:02d}  {entry['name'] or '(unnamed)'}")
        if self.index is not None:
            self.listbox.selection_set(self.index)
            self.listbox.see(self.index)

    def show_entry(self, index):
        self.loading = True
        self.index = index
        self.name_entry.configure(state="normal")
        self.body.configure(state="normal")
        self.body.delete("1.0", tk.END)
        if index is not None:
            entry = self.entries[index]
            self.name_var.set(entry["name"])
            self.body.insert("1.0", entry["text"])
        else:
            self.name_var.set("")
            self.name_entry.configure(state="disabled")
            self.body.configure(state="disabled")
        self.body.edit_reset()
        self.body.edit_modified(False)
        self.loading = False
        self.refresh_list()
        self.update_preview()

    def update_preview(self):
        content = self.body.get("1.0", "end-1c")
        self.preview.configure(state="normal")
        self.preview.delete("1.0", tk.END)
        self.preview.insert("1.0", visible_whitespace(content))
        self.preview.configure(state="disabled")
        character_count = len(content)
        difference = character_count - SUGGESTED_CHARACTER_GOAL
        if difference < 0:
            goal_status = f"{-difference} characters below goal"
        elif difference > 0:
            goal_status = f"{difference} characters above goal"
        else:
            goal_status = "goal reached (difference: 0)"
        line_count = content.count("\n") + 1
        line_label = "line" if line_count == 1 else "lines"
        self.count_var.set(
            f"{character_count} characters · {line_count} text {line_label}\n"
            f"Suggested goal: {SUGGESTED_CHARACTER_GOAL} characters · {goal_status}"
        )

    def name_changed(self, *args):
        if not self.loading:
            self.commit_editor()
            if self.index is not None:
                self.listbox.delete(self.index)
                self.listbox.insert(self.index, f"{self.index + 1:02d}  {self.name_var.get() or '(unnamed)'}")
                self.listbox.selection_set(self.index)
            self.status_var.set("Unsaved changes")

    def body_changed(self, event=None):
        if self.body.edit_modified():
            self.body.edit_modified(False)
            if not self.loading:
                self.commit_editor()
                self.update_preview()
                self.status_var.set("Unsaved changes")

    def select(self, event=None):
        selection = self.listbox.curselection()
        if selection and selection[0] != self.index:
            self.commit_editor()
            self.show_entry(selection[0])

    def add(self):
        self.commit_editor()
        self.entries.append({"name": "New text", "text": ""})
        self.show_entry(len(self.entries) - 1)
        self.status_var.set("Unsaved changes")
        self.name_entry.focus_set()
        self.name_entry.selection_range(0, tk.END)

    def delete(self):
        if self.index is None:
            return
        if not messagebox.askyesno("Delete text", f"Delete “{self.name_var.get()}”?", parent=self.window):
            return
        self.entries.pop(self.index)
        self.show_entry(min(self.index, len(self.entries) - 1) if self.entries else None)
        self.status_var.set("Unsaved changes")

    def reorder(self, target):
        if self.index is None or not 0 <= target < len(self.entries) or target == self.index:
            return
        self.commit_editor()
        self.entries.insert(target, self.entries.pop(self.index))
        self.show_entry(target)
        self.status_var.set("Unsaved changes")

    def move(self, delta):
        if self.index is not None:
            self.reorder(self.index + delta)

    def start_drag(self, event):
        if self.entries:
            self.drag_index = self.listbox.nearest(event.y)

    def drag(self, event):
        if self.drag_index is not None:
            self.commit_editor()
            # Ensure the dragged row, rather than the previously selected row, moves.
            if self.index != self.drag_index:
                self.show_entry(self.drag_index)
            self.reorder(self.listbox.nearest(event.y))
            self.drag_index = self.index
            return "break"

    def end_drag(self, event):
        self.drag_index = None

    def save(self):
        self.commit_editor()
        try:
            save_texts(get__file_path(TEXT_FILE_NAME), self.entries)
        except (OSError, ValueError) as error:
            messagebox.showerror("Cannot save texts", str(error), parent=self.window)
            return False
        self.app.text_entries = copy.deepcopy(self.entries)
        self.app.refresh_text_list()
        self.saved_entries = copy.deepcopy(self.entries)
        self.status_var.set("Changes saved")
        return True

    def discard(self):
        self.commit_editor()
        if self.entries != self.saved_entries and not messagebox.askyesno(
                "Discard changes", "Discard unsaved changes to your texts?", parent=self.window):
            return
        self.entries = copy.deepcopy(self.saved_entries)
        self.show_entry(0 if self.entries else None)
        self.status_var.set("Changes discarded")

    def close(self):
        self.commit_editor()
        if self.entries != self.saved_entries:
            answer = messagebox.askyesnocancel("Unsaved texts", "Save changes before closing?", parent=self.window)
            if answer is None or (answer and not self.save()):
                return False
        self.window.destroy()
        self.app.text_manager = None
        return True
