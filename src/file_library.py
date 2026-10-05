#!/usr/bin/env python3
"""File Library - GTK 4 app that lists videos, images, documents and music from
several source folders, with a cached index and search."""
import os
import sys
import threading
import time

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

import file_library_core as core  # noqa: E402

APP_ID = "org.filelibrary.FileLibrary"
TITLE = "File Library"
KIND_ICON = {"v": "video-x-generic", "i": "image-x-generic", "d": "x-office-document",
             "m": "audio-x-generic"}
# (key, action name, description). The About window and the accelerators both use this list.
SHORTCUTS = [
    ("F1", "open-folder", "Open the folder that contains the selected file"),
    ("F2", "select-file", "Select the file in the file manager"),
    ("F3", "copy-path", "Copy the full path of the selected file"),
    ("F4", "copy-filename", "Copy the file name without its extension"),
    ("F5", "rescan-all", "Rescan all folders"),
    ("F6", "export-list", "Export the shown list as a .txt file"),
    ("F7", "save-config", "Save config"),
]
CSS = b"""
.chip { padding: 0 10px; min-height: 22px; font-size: 11px; border-radius: 11px; }
.chip:checked { background-image: none; background-color: #26a269; color: #ffffff; border-color: #1e8a58; }
.chip:checked:hover { background-color: #2bb673; }
button.hide-btn, button.hide-btn:checked { background-image: none; background-color: transparent;
                                           border-color: transparent; box-shadow: none; }
button.hide-btn:hover, button.hide-btn:checked:hover { background-color: alpha(currentColor, 0.1); }
button.hide-btn.hide-scanning { color: #f57900; }
.kbd { font-family: monospace; font-weight: bold; padding: 2px 12px; border-radius: 6px;
       border: 1px solid alpha(currentColor, 0.35); }
.dirty-label { color: #e5a50a; }
.dim-label { opacity: 0.65; }
.note { padding: 4px 12px; font-size: 12px; }
"""


class Folder:
    def __init__(self, path, enabled=True, types=("v",)):
        self.path = path
        self.enabled = enabled
        self.types = set(types)
        self.tree = None
        self.scanned = None
        self.scanned_types = None
        self.busy = False


def esc(text):
    return GLib.markup_escape_text(text)


def highlight(name, query, case_sensitive, ignore_delimiters=False):
    span = core.find_in_filename(name, query, case_sensitive, ignore_delimiters) if query else None
    if not span or span[0] == span[1]:
        return esc(name)
    i, j = span
    return (esc(name[:i]) + '<span background="#f5d76e" foreground="#000000">'
            + esc(name[i:j]) + "</span>" + esc(name[j:]))


def fmt_size_total(size):
    mb = core.mb(size)
    return f"{mb / 1024:.2f} GB" if mb >= 1024 else f"{mb:.1f} MB"


class AboutWindow(Gtk.Window):
    """About dialog with three tabs: About, Shortcuts and License."""

    def __init__(self, parent):
        super().__init__(transient_for=parent, modal=True, title=f"About {core.APP_NAME}")
        self.set_default_size(500, 520)
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        for side in ("top", "bottom", "start", "end"):
            getattr(root, f"set_margin_{side}")(14)
        self.set_child(root)

        self.stack = Gtk.Stack(vexpand=True, transition_type=Gtk.StackTransitionType.CROSSFADE)
        switcher = Gtk.StackSwitcher(stack=self.stack, halign=Gtk.Align.CENTER)
        root.append(switcher)
        root.append(self.stack)
        self.stack.add_titled(self._about_page(), "about", "About")
        self.stack.add_titled(self._shortcuts_page(), "shortcuts", "Shortcuts")
        self.stack.add_titled(self._license_page(), "license", "License")

        close = Gtk.Button(label="Close", halign=Gtk.Align.END)
        close.connect("clicked", lambda *_: self.close())
        root.append(close)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

    def _on_key(self, _controller, keyval, _keycode, _state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False

    def _about_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, valign=Gtk.Align.CENTER)
        icon = Gtk.Image.new_from_icon_name("file-library")
        icon.set_pixel_size(96)
        name = Gtk.Label()
        name.set_markup(f'<span size="x-large" weight="bold">{esc(core.APP_NAME)}</span>')
        version = Gtk.Label(label=f"Version {core.__version__}")
        comments = Gtk.Label(label=core.COMMENTS, wrap=True, justify=Gtk.Justification.CENTER)
        comments.set_margin_top(6)
        link = Gtk.LinkButton.new_with_label(core.REPO_URL, core.REPO_URL.replace("https://", ""))
        copyright_label = Gtk.Label(label=core.COPYRIGHT)
        copyright_label.set_margin_top(6)
        legal = Gtk.Label(label="Released under the MIT License.\nThis program comes with absolutely no warranty.",
                          justify=Gtk.Justification.CENTER)
        legal.add_css_class("dim-label")
        for w in (icon, name, version, comments, link, copyright_label, legal):
            box.append(w)
        return box

    def _shortcuts_page(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14, valign=Gtk.Align.CENTER,
                      halign=Gtk.Align.CENTER)
        heading = Gtk.Label()
        heading.set_markup('<span size="large" weight="bold">Keyboard shortcuts</span>')
        box.append(heading)
        grid = Gtk.Grid(row_spacing=10, column_spacing=18, halign=Gtk.Align.CENTER)
        for row, (key, _action, text) in enumerate(SHORTCUTS):
            key_label = Gtk.Label(label=key, halign=Gtk.Align.CENTER)
            key_label.add_css_class("kbd")
            grid.attach(key_label, 0, row, 1, 1)
            grid.attach(Gtk.Label(label=text, xalign=0), 1, row, 1, 1)
        box.append(grid)
        tip = Gtk.Label(label="F1 to F4 work on the file that is selected in the list.\n"
                              "You can also right-click a file to reach these four actions.",
                        justify=Gtk.Justification.CENTER)
        tip.add_css_class("dim-label")
        box.append(tip)
        return box

    def _license_page(self):
        label = Gtk.Label(label=core.LICENSE_TEXT, wrap=True, selectable=True, xalign=0, yalign=0)
        label.set_margin_top(6)
        label.set_margin_bottom(6)
        label.set_margin_start(6)
        label.set_margin_end(6)
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(label)
        return scroll


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=TITLE)
        self.window_state = core.load_window_state()
        self.set_default_size(self.window_state.get("width", 1000),
                              self.window_state.get("height", 680))
        if self.window_state.get("maximized"):
            self.maximize()

        self.folders = []
        self.dirty = False
        self.queue = []
        self.lock = threading.Lock()
        self.scanning = False
        self.cancel = threading.Event()
        self.total_jobs = 0
        self.done_jobs = 0
        self.note_timer = 0
        self.rebuild_pending = False
        self._applying = False          # True while settings are applied from code
        self._counts = {}               # folder path -> (files, bytes) of its rows in the list
        self._ctx_folder_path = None    # tree path of the folder row last right-clicked
        self.view_types = set(core.TYPE_ORDER)

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self._build_ui()
        self._build_actions()
        self._load_state()
        self.connect("close-request", self.on_close_request)

    # ------------------------------------------------------------ UI
    def _make_button(self, icon, text, callback):
        button = Gtk.Button()
        box = Gtk.Box(spacing=6)
        image = Gtk.Image.new_from_icon_name(icon)
        label = Gtk.Label(label=text)
        box.append(image)
        box.append(label)
        button.set_child(box)
        button.connect("clicked", lambda *_: callback())
        button.image = image
        button.label = label
        return button

    def _build_ui(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(root)

        toolbar = Gtk.Box(spacing=6)
        toolbar.set_margin_top(8)
        toolbar.set_margin_bottom(8)
        toolbar.set_margin_start(12)
        toolbar.set_margin_end(12)
        self.btn_add = self._make_button("folder-new-symbolic", "Add folder", self.on_add)
        self.btn_scan = self._make_button("view-refresh-symbolic", "Rescan all", self.on_scan_clicked)
        self.btn_save = self._make_button("document-save-symbolic", "Save config", self.on_save)
        self.btn_export = self._make_button("document-send-symbolic", "Export list", self.on_export)
        self.btn_about = self._make_button("help-about-symbolic", "About", self.on_about)
        self.btn_scan.set_tooltip_text("Rescan all folders (F5)")
        self.btn_save.set_tooltip_text("Save the folders, search options and type filter (F7)")
        self.btn_export.set_tooltip_text("Export the shown list as a text file (F6)")
        for w in (self.btn_add, self.btn_scan):
            toolbar.append(w)
        toolbar.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        toolbar.append(self.btn_save)
        toolbar.append(self.btn_export)
        toolbar.append(Gtk.Box(hexpand=True))
        toolbar.append(self.btn_about)
        root.append(toolbar)
        root.append(Gtk.Separator())

        self.note = Gtk.Label(xalign=0, wrap=True)
        self.note.add_css_class("note")
        self.note.set_size_request(-1, 28)
        root.append(self.note)
        root.append(Gtk.Separator())

        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, vexpand=True)
        paned.set_position(self.window_state.get("paned", 310))
        self.paned = paned
        paned.set_shrink_start_child(False)
        root.append(paned)

        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        heading = Gtk.Label(label="Folders and file types", xalign=0)
        heading.add_css_class("dim-label")
        heading.set_margin_top(10)
        heading.set_margin_bottom(6)
        heading.set_margin_start(12)
        side.append(heading)
        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(self.listbox)
        side.append(scroll)
        paned.set_start_child(side)

        main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main.set_margin_top(10)
        main.set_margin_start(12)
        main.set_margin_end(12)
        main.set_margin_bottom(8)
        search_row = Gtk.Box(spacing=10)
        self.search = Gtk.SearchEntry(hexpand=True, placeholder_text="Search file names, for example garden (extension is ignored)")
        self.search.connect("search-changed", lambda *_: self.refresh_tree())
        self.case_check = Gtk.CheckButton(label="Case sensitive")
        self.case_check.connect("toggled", self.on_search_option_toggled)
        search_row.append(self.search)
        self.delim_check = Gtk.CheckButton(label="Ignore delimiter")
        self.delim_check.set_tooltip_text(
            "Ignore spaces, dots, commas, dashes and underscores when searching")
        self.delim_check.connect("toggled", self.on_search_option_toggled)
        search_row.append(self.case_check)
        search_row.append(self.delim_check)
        main.append(search_row)

        self.store = Gtk.TreeStore(str, str, str, str, str, str)  # icon, markup, size, file path, tooltip, folder key
        self.view = Gtk.TreeView(model=self.store, headers_visible=False, enable_search=False)
        col = Gtk.TreeViewColumn()
        col.set_expand(True)
        pix = Gtk.CellRendererPixbuf()
        col.pack_start(pix, False)
        col.add_attribute(pix, "icon-name", 0)
        txt = Gtk.CellRendererText(ellipsize=Pango.EllipsizeMode.END, xpad=4)
        col.pack_start(txt, True)
        col.add_attribute(txt, "markup", 1)
        self.view.append_column(col)
        self.view.set_tooltip_column(4)
        size_col = Gtk.TreeViewColumn()
        size_txt = Gtk.CellRendererText(xalign=1.0, xpad=8)
        size_col.pack_start(size_txt, False)
        size_col.add_attribute(size_txt, "text", 2)
        self.view.append_column(size_col)
        tree_scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        tree_scroll.set_child(self.view)
        main.append(tree_scroll)
        bottom = Gtk.Box(spacing=6)
        hint = Gtk.Label(label="Right-click a file, or select it and press F1 to F4.", xalign=0, hexpand=True,
                         ellipsize=Pango.EllipsizeMode.END)
        hint.add_css_class("dim-label")
        bottom.append(hint)
        show_label = Gtk.Label(label="Show:")
        show_label.add_css_class("dim-label")
        bottom.append(show_label)
        self.filter_chips = {}
        for key in core.TYPE_ORDER:
            chip = Gtk.ToggleButton(label=core.TYPES[key][0], active=True)
            chip.add_css_class("chip")
            chip.set_tooltip_text(f"Show or hide {core.TYPES[key][0].lower()} in the list")
            chip.connect("toggled", self.on_view_chip_toggled, key)
            self.filter_chips[key] = chip
            bottom.append(chip)
        main.append(bottom)
        paned.set_end_child(main)
        self._build_context_menu()

        root.append(Gtk.Separator())
        status = Gtk.Box(spacing=12)
        status.set_margin_top(6)
        status.set_margin_bottom(6)
        status.set_margin_start(12)
        status.set_margin_end(12)
        self.count_label = Gtk.Label(xalign=0, hexpand=True)
        self.dirty_label = Gtk.Label(label="Unsaved changes", visible=False)
        self.dirty_label.add_css_class("dirty-label")
        self.status_label = Gtk.Label(xalign=1)
        self.progress = Gtk.ProgressBar(visible=False)
        self.progress.set_size_request(140, -1)
        self.progress.set_valign(Gtk.Align.CENTER)
        for w in (self.count_label, self.dirty_label, self.status_label, self.progress):
            status.append(w)
        root.append(status)

    def on_close_request(self, _window):
        state = dict(self.window_state)
        state["maximized"] = self.is_maximized()
        if not state["maximized"] and self.get_width() > 0 and self.get_height() > 0:
            state["width"], state["height"] = self.get_width(), self.get_height()
        state["paned"] = self.paned.get_position()
        try:
            core.save_window_state(state)
        except OSError:
            pass
        return False  # let the window close

    # ------------------------------------------------------------ state
    def _load_state(self):
        cache = core.load_cache()
        cfg = core.load_config()
        self._applying = True
        self.case_check.set_active(cfg["case_sensitive"])
        self.delim_check.set_active(cfg["ignore_delimiter"])
        self.view_types = set(cfg["view_types"])
        for key, chip in self.filter_chips.items():
            chip.set_active(key in self.view_types)
        self._applying = False
        for item in cfg["folders"]:
            f = Folder(item["path"], item["enabled"], item["types"])
            entry = cache.get(f.path)
            if entry and sorted(entry.get("types", [])) == sorted(f.types):
                f.tree = entry.get("tree")
                f.scanned = entry.get("scanned")
                f.scanned_types = set(f.types)
            self.folders.append(f)
        self.rebuild_folders()
        self.refresh_tree()
        self._show_cache_time()
        missing = [f for f in self.folders if f.tree is None and f.types]
        if missing:
            GLib.idle_add(lambda: self.start_scan(missing) or GLib.SOURCE_REMOVE)

    def _save_cache(self):
        entries = {f.path: {"types": sorted(f.scanned_types), "scanned": f.scanned, "tree": f.tree}
                   for f in self.folders if f.tree is not None and f.scanned_types}
        try:
            core.save_cache(entries)
        except OSError as err:
            self.show_note(f"Couldn't write the cache: {err}")

    def _show_cache_time(self):
        times = [f.scanned for f in self.folders if f.scanned]
        if not times:
            self.status_label.set_text("No cache yet")
            return
        t = time.localtime(max(times))
        today = time.localtime()
        same_day = (t.tm_year, t.tm_yday) == (today.tm_year, today.tm_yday)
        text = time.strftime("%H:%M", t) if same_day else time.strftime("%Y-%m-%d %H:%M", t)
        self.status_label.set_text(f"Cache updated {'today, ' if same_day else ''}{text}")

    def show_note(self, text, keep=False):
        self.note.set_text(text)
        if self.note_timer:
            GLib.source_remove(self.note_timer)
            self.note_timer = 0
        if text and not keep:
            self.note_timer = GLib.timeout_add_seconds(5, self._clear_note)

    def _clear_note(self):
        self.note_timer = 0
        self.note.set_text("")
        return GLib.SOURCE_REMOVE

    def set_dirty(self, message=None):
        self.dirty = True
        self.set_title(TITLE + " \u2022")
        self.dirty_label.set_visible(True)
        self.btn_save.add_css_class("suggested-action")
        if message:
            self.show_note(f"{message} Not saved yet. Press Save config to keep it after a restart.")

    def clear_dirty(self):
        self.dirty = False
        self.set_title(TITLE)
        self.dirty_label.set_visible(False)
        self.btn_save.remove_css_class("suggested-action")

    # ------------------------------------------------------------ folder list
    def rebuild_soon(self):
        if not self.rebuild_pending:
            self.rebuild_pending = True
            GLib.idle_add(self._do_rebuild)

    def _do_rebuild(self):
        self.rebuild_pending = False
        self.rebuild_folders()
        return GLib.SOURCE_REMOVE

    def rebuild_folders(self):
        child = self.listbox.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.listbox.remove(child)
            child = nxt
        for folder in self.folders:
            self.listbox.append(self._folder_row(folder))

    def _folder_row(self, folder):
        box = Gtk.Box(spacing=8)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(12)
        box.set_margin_end(12)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True)
        name = folder.path.rstrip("/").split("/")[-1] or folder.path
        title = Gtk.Label(label=name, xalign=0, ellipsize=Pango.EllipsizeMode.END)
        path = Gtk.Label(label=folder.path, xalign=0, ellipsize=Pango.EllipsizeMode.MIDDLE)
        path.add_css_class("dim-label")
        col.append(title)
        col.append(path)
        chips = Gtk.FlowBox(selection_mode=Gtk.SelectionMode.NONE, column_spacing=4, row_spacing=4,
                            min_children_per_line=1, max_children_per_line=4, homogeneous=False,
                            halign=Gtk.Align.START, hexpand=True, activate_on_single_click=False)
        chips.set_margin_top(4)
        for key in core.TYPE_ORDER:
            chip = Gtk.ToggleButton(label=core.TYPES[key][0])
            chip.add_css_class("chip")
            chip.set_tooltip_text(core.type_hint(key))
            chip.set_active(key in folder.types)
            chip.connect("toggled", self.on_chip_toggled, folder, key)
            chips.append(chip)
        col.append(chips)
        if not folder.types:
            hint = Gtk.Label(label="Select a file type to scan this folder", xalign=0, wrap=True)
            hint.add_css_class("dim-label")
            hint.set_margin_top(2)
            col.append(hint)
        box.append(col)

        hide = Gtk.ToggleButton(valign=Gtk.Align.START)
        hide.add_css_class("flat")
        hide.add_css_class("hide-btn")
        hide.set_active(not folder.enabled)
        self._style_hide_button(hide, folder)
        hide.connect("toggled", self.on_hide_toggled, folder)
        box.append(hide)

        rescan = Gtk.Button()
        rescan.add_css_class("flat")
        rescan.set_valign(Gtk.Align.START)
        if folder.busy:
            rescan.set_child(Gtk.Spinner(spinning=True))
            rescan.set_tooltip_text("Scanning\u2026")
            rescan.set_sensitive(False)
        else:
            rescan.set_icon_name("view-refresh-symbolic")
            rescan.set_tooltip_text("Rescan this folder")
            rescan.connect("clicked", lambda *_: self.rescan_folder(folder))
        box.append(rescan)

        remove = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        remove.add_css_class("flat")
        remove.set_valign(Gtk.Align.START)
        remove.set_tooltip_text("Remove this folder")
        remove.connect("clicked", lambda *_: GLib.idle_add(self._remove_now, folder))
        box.append(remove)
        return box

    def _style_hide_button(self, button, folder):
        hidden = not folder.enabled
        button.set_icon_name("view-conceal-symbolic" if hidden else "view-reveal-symbolic")
        if hidden and folder.busy:
            button.add_css_class("hide-scanning")  # hidden and being scanned: orange
            button.set_tooltip_text("Hidden from the list, scanning in progress")
        else:
            button.remove_css_class("hide-scanning")
            button.set_tooltip_text("Hide the files of this folder from the list" if not hidden
                                    else "Hidden from the list. Click to show it again")

    def on_hide_toggled(self, button, folder):
        hidden = button.get_active()
        if folder.enabled == (not hidden):
            return
        folder.enabled = not hidden
        self._style_hide_button(button, folder)   # the icon changes at once
        self.set_dirty("Folder hidden from the list." if hidden else "Folder shown in the list.")
        # the list is updated afterwards, so a large library never delays the button
        GLib.idle_add(self._apply_hide, folder, priority=GLib.PRIORITY_LOW)

    def _apply_hide(self, folder):
        if folder in self.folders:
            if folder.enabled:
                self._insert_root(folder)
            else:
                self._remove_root(folder.path)
            self._update_count_label()
        return GLib.SOURCE_REMOVE

    def on_chip_toggled(self, chip, folder, key):
        if chip.get_active():
            if key in folder.types:
                return
            folder.types.add(key)
        else:
            if key not in folder.types:
                return
            folder.types.discard(key)
            if not folder.types:
                self._clear_folder_scan(folder)
                self.set_dirty("File types changed. No type is selected, so this folder is not scanned.")
                return
        self.set_dirty("File types changed.")
        self.start_scan([folder])

    def _clear_folder_scan(self, folder):
        """Forget the scan of a folder that has no file type selected."""
        with self.lock:
            if folder in self.queue:
                self.queue.remove(folder)
            folder.busy = False
        folder.tree = None
        folder.scanned = None
        folder.scanned_types = None
        self.refresh_tree()
        self._save_cache()
        self.rebuild_soon()

    def on_search_option_toggled(self, _check):
        self.refresh_tree()
        if not self._applying:
            self.set_dirty("Search option changed.")

    def on_view_chip_toggled(self, chip, key):
        if self._applying:
            return
        if chip.get_active():
            self.view_types.add(key)
        else:
            if key not in self.view_types:
                return
            if len(self.view_types) == 1:  # keep at least one type shown
                self._applying = True
                chip.set_active(True)
                self._applying = False
                return
            self.view_types.discard(key)
        self.refresh_tree()
        self.set_dirty("Display filter changed.")

    # ------------------------------------------------------------ actions
    def _build_actions(self):
        handlers = {
            "open-folder": self.on_open_folder,
            "select-file": self.on_select_in_manager,
            "copy-path": self.on_copy_path,
            "copy-filename": self.on_copy_filename,
            "rescan-all": self.rescan_all,
            "export-list": self.on_export,
            "save-config": self.on_save,
        }
        app = self.get_application()
        for key, name, _text in SHORTCUTS:
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", lambda _a, _p, fn=handlers[name]: fn())
            self.add_action(action)
            app.set_accels_for_action(f"win.{name}", [key])
        collapse = Gio.SimpleAction.new("collapse-folder", None)
        collapse.connect("activate", lambda *_: self.on_collapse_folder())
        self.add_action(collapse)

    def on_add(self):
        dialog = Gtk.FileDialog(title="Choose a folder to add")
        dialog.select_folder(self, None, self._on_folder_chosen)

    def _on_folder_chosen(self, dialog, result):
        try:
            gfile = dialog.select_folder_finish(result)
        except GLib.Error:
            return
        path = gfile.get_path()
        if not path:
            return
        if any(f.path == path for f in self.folders):
            self.show_note("That folder is already in the list.")
            return
        folder = Folder(path, True, set())
        self.folders.append(folder)
        self.rebuild_folders()
        self.set_dirty("Folder added. Select a file type to start the scan.")

    def rescan_folder(self, folder):
        if not folder.types:
            self.show_note("Select a file type for this folder first.")
            return
        if self.scanning:
            self.show_note("Queued. It will be scanned after the current folder.")
        else:
            self.show_note(f"Rescanning {folder.path}\u2026")
        self.start_scan([folder])

    def _remove_now(self, folder):
        if folder in self.folders:
            with self.lock:
                if folder in self.queue:
                    self.queue.remove(folder)
            self.folders.remove(folder)
            self.rebuild_folders()
            self.refresh_tree()
            self._save_cache()
            self.set_dirty(f"Removed {folder.path}.")
        return GLib.SOURCE_REMOVE

    # ------------------------------------------------------------ context menu
    def _build_context_menu(self):
        accel = {name: key for key, name, _text in SHORTCUTS}
        file_menu = Gio.Menu()
        for label, name in (("Open containing folder", "open-folder"),
                            ("Select file in manager", "select-file"),
                            ("Copy file path", "copy-path"),
                            ("Copy file name", "copy-filename")):
            item = Gio.MenuItem.new(label, f"win.{name}")
            item.set_attribute_value("accel", GLib.Variant.new_string(accel[name]))
            file_menu.append_item(item)
        folder_menu = Gio.Menu()
        folder_menu.append("Collapse folder", "win.collapse-folder")
        self.ctx_popover = self._make_popover(file_menu)
        self.ctx_folder_popover = self._make_popover(folder_menu)
        click = Gtk.GestureClick(button=3)
        click.connect("pressed", self.on_view_right_click)
        self.view.add_controller(click)

    def _make_popover(self, menu):
        popover = Gtk.PopoverMenu.new_from_model(menu)
        popover.set_parent(self.view)
        popover.set_has_arrow(False)
        popover.set_halign(Gtk.Align.START)
        self.view.connect("destroy", lambda *_: popover.unparent())
        return popover

    def _selected_file(self):
        """Full path of the file row selected in the list, or '' for none or a folder."""
        model, it = self.view.get_selection().get_selected()
        return model.get_value(it, 3) if it is not None else ""

    def on_view_right_click(self, gesture, _n_press, x, y):
        bx, by = self.view.convert_widget_to_bin_window_coords(int(x), int(y))
        hit = self.view.get_path_at_pos(bx, by)
        if not hit:
            return
        tree_path = hit[0]
        file_path = self.store.get_value(self.store.get_iter(tree_path), 3)
        self.view.get_selection().select_path(tree_path)
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        if file_path:
            popover = self.ctx_popover
        else:  # a folder row
            self._ctx_folder_path = tree_path
            popover = self.ctx_folder_popover
        popover.set_pointing_to(rect)
        popover.popup()

    def on_collapse_folder(self):
        """Collapse the right-clicked folder and everything below it, not its parent."""
        if self._ctx_folder_path is not None:
            self.view.collapse_row(self._ctx_folder_path)

    def _copy_text(self, text):
        clipboard = self.get_clipboard()
        try:
            clipboard.set_text(text)
        except AttributeError:
            clipboard.set(text)

    def on_copy_path(self):
        path = self._selected_file()
        if not path:
            self.show_note("Select a file in the list first.")
            return
        self._copy_text(path)
        self.show_note(f"Copied to clipboard: {path}")

    def on_copy_filename(self):
        path = self._selected_file()
        if not path:
            self.show_note("Select a file in the list first.")
            return
        name = os.path.splitext(os.path.basename(path))[0]
        self._copy_text(name)
        self.show_note(f"Copied file name to clipboard: {name}")

    def on_open_folder(self):
        path = self._selected_file()
        if not path:
            self.show_note("Select a file in the list first.")
            return
        folder = os.path.dirname(path)
        if not os.path.isdir(folder):
            self.show_note(f"Folder not found: {folder}")
            return
        self._open_folder(folder)

    def on_select_in_manager(self):
        path = self._selected_file()
        if not path:
            self.show_note("Select a file in the list first.")
            return
        if not os.path.exists(path):
            folder = os.path.dirname(path)
            if os.path.isdir(folder):
                self.show_note(f"File not found, opening its folder instead: {path}")
                self._open_folder(folder, keep_note=True)
            else:
                self.show_note(f"File not found: {path}")
            return
        try:
            # Opens the default file manager with the file selected (GTK 4.10+).
            launcher = Gtk.FileLauncher.new(Gio.File.new_for_path(path))
            launcher.open_containing_folder(self, None, self._on_select_done, path)
        except (AttributeError, TypeError):
            self._select_via_dbus(path)

    def _on_select_done(self, launcher, result, path):
        try:
            launcher.open_containing_folder_finish(result)
        except GLib.Error:
            self._select_via_dbus(path)
            return
        self.show_note(f"Selected in the file manager: {path}")

    def _select_via_dbus(self, path):
        """Ask the file manager to show the file, the standard FileManager1 interface."""
        try:
            bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
            uri = Gio.File.new_for_path(path).get_uri()
            bus.call_sync("org.freedesktop.FileManager1", "/org/freedesktop/FileManager1",
                          "org.freedesktop.FileManager1", "ShowItems",
                          GLib.Variant("(ass)", ([uri], "")), None,
                          Gio.DBusCallFlags.NONE, 3000, None)
        except GLib.Error:
            self._open_folder(os.path.dirname(path))  # last resort: just open the folder
            return
        self.show_note(f"Selected in the file manager: {path}")

    def _open_folder(self, folder, keep_note=False):
        try:
            uri = Gio.File.new_for_path(folder).get_uri()
            Gio.AppInfo.launch_default_for_uri(uri, None)
        except GLib.Error as err:
            self.show_note(f"Couldn't open the folder: {err.message}")
            return
        if not keep_note:
            self.show_note(f"Opened folder: {folder}")

    def on_save(self):
        if not self.dirty:
            self.show_note("Nothing to save. The config is up to date.")
            return
        try:
            core.save_config(
                [{"path": f.path, "enabled": f.enabled, "types": f.types} for f in self.folders],
                {"case_sensitive": self.case_check.get_active(),
                 "ignore_delimiter": self.delim_check.get_active(),
                 "view_types": self.view_types})
        except OSError as err:
            self.show_note(f"Couldn't save the config: {err}")
            return
        self.clear_dirty()
        self.show_note("Config saved.")

    def on_export(self):
        roots = self.visible_roots()
        if not roots:
            self.show_note("Nothing to export. The list is empty.")
            return
        dialog = Gtk.FileDialog(title="Export list as text", initial_name="file-library-list.txt")
        dialog.save(self, None, self._on_export_chosen)

    def _on_export_chosen(self, dialog, result):
        try:
            gfile = dialog.save_finish(result)
        except GLib.Error:
            return
        path = gfile.get_path()
        if not path:
            return
        if not path.lower().endswith(".txt"):
            path += ".txt"
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(core.format_export(self.visible_roots()))
        except OSError as err:
            self.show_note(f"Couldn't write the file: {err}")
            return
        self.show_note(f"Exported the shown list to {path}")

    def on_about(self):
        AboutWindow(self).present()

    # ------------------------------------------------------------ list view
    def visible_roots(self):
        query = self.search.get_text()
        case = self.case_check.get_active()
        roots = []
        for f in self.folders:
            types = f.types & self.view_types
            if f.enabled and f.tree is not None and types:
                node = core.filter_tree(f.tree, types, query, case, self.delim_check.get_active())
                if node is not None:
                    roots.append((f.path, node))
        return roots

    def refresh_tree(self):
        query = self.search.get_text()
        case = self.case_check.get_active()
        self.view.set_model(None)  # clearing and filling a detached model is much faster
        self.store.clear()
        self._counts = {}
        for path, node in self.visible_roots():
            self._add_root(path, node, query, case)
        self.view.set_model(self.store)
        self.view.expand_all()
        self._update_count_label()

    def _add_root(self, path, node, query, case, position=-1):
        label = os.path.basename(path.rstrip("/")) or path
        row = ["folder", f"<b>{esc(label)}</b>", "", "", esc(path), path]
        it = self.store.append(None, row) if position < 0 else self.store.insert(None, position, row)
        self._fill(it, node, query, case, path)
        self._counts[path] = core.count_tree(node)
        return it

    def _root_rows(self):
        """Top-level rows as (folder path, iter), in list order."""
        rows = []
        it = self.store.get_iter_first()
        while it is not None:
            rows.append((self.store.get_value(it, 5), it))
            it = self.store.iter_next(it)
        return rows

    def _remove_root(self, path):
        for key, it in self._root_rows():
            if key == path:
                self.view.collapse_row(self.store.get_path(it))  # lets the view drop the rows at once
                self.store.remove(it)
                break
        self._counts.pop(path, None)

    def _insert_root(self, folder):
        types = folder.types & self.view_types
        if folder.tree is None or not types:
            return
        keys = [key for key, _it in self._root_rows()]
        if folder.path in keys:
            return
        query = self.search.get_text()
        case = self.case_check.get_active()
        node = core.filter_tree(folder.tree, types, query, case, self.delim_check.get_active())
        if node is None:
            return
        position = sum(1 for f in self.folders[:self.folders.index(folder)] if f.path in keys)
        it = self._add_root(folder.path, node, query, case, position)
        self.view.expand_row(self.store.get_path(it), True)

    def _update_count_label(self):
        count = sum(n for n, _size in self._counts.values())
        size = sum(s for _n, s in self._counts.values())
        self.count_label.set_text(f"{count} files \u00b7 {fmt_size_total(size)} shown")

    def _fill(self, parent, node, query, case, base):
        for name, kind, nbytes in node["files"]:
            full = os.path.join(base, name)
            self.store.append(parent, [KIND_ICON[kind], highlight(name, query, case, self.delim_check.get_active()),
                                       f"{core.mb(nbytes):.2f} MB", full, esc(full), ""])
        for sub in node["dirs"]:
            sub_path = os.path.join(base, sub["name"])
            it = self.store.append(parent, ["folder", f"<b>{esc(sub['name'])}</b>", "", "", esc(sub_path), ""])
            self._fill(it, sub, query, case, sub_path)

    # ------------------------------------------------------------ scanning
    def on_scan_clicked(self):
        if self.scanning:
            self.cancel.set()
            return
        self.rescan_all()

    def rescan_all(self):
        if self.scanning:
            self.show_note("A scan is already running.")
            return
        if not self.folders:
            self.show_note("Add a folder first.")
            return
        todo = [f for f in self.folders if f.types]
        if not todo:
            self.show_note("Select a file type for a folder first.")
            return
        self.show_note("Rescanning all folders\u2026")
        self.start_scan(todo)

    def start_scan(self, folders):
        folders = [f for f in folders if f.types]  # a folder without a file type is never scanned
        if not folders:
            return
        with self.lock:
            for f in folders:
                if f not in self.queue:
                    self.queue.append(f)
                f.busy = True
            self.total_jobs = max(self.total_jobs, self.done_jobs + len(self.queue))
            if self.scanning:
                self.rebuild_soon()
                return
            self.scanning = True
            self.cancel.clear()
            self.done_jobs = 0
            self.total_jobs = len(self.queue)
        self.btn_scan.label.set_text("Stop scan")
        self.btn_scan.image.set_from_icon_name("media-playback-stop-symbolic")
        self.progress.set_visible(True)
        self.progress.set_fraction(0)
        self.rebuild_soon()
        threading.Thread(target=self._worker, daemon=True).start()

    def _worker(self):
        while True:
            with self.lock:
                if self.cancel.is_set() or not self.queue:
                    cancelled = self.cancel.is_set()
                    self.queue.clear()
                    self.scanning = False
                    break
                folder = self.queue.pop(0)
                path, types = folder.path, set(folder.types)
            GLib.idle_add(self._progress, path, 0)
            tree = core.scan_folder(path, types,
                                    lambda n, p=path: GLib.idle_add(self._progress, p, n),
                                    self.cancel)
            GLib.idle_add(self._scan_done, folder, types, tree)
        GLib.idle_add(self._scan_finished, cancelled)

    def _progress(self, path, count):
        self.status_label.set_text(f"Scanning {path} \u00b7 {count} files checked")
        if self.total_jobs:
            self.progress.set_fraction(min(0.99, self.done_jobs / self.total_jobs))
        return GLib.SOURCE_REMOVE

    def _scan_done(self, folder, types, tree):
        self.done_jobs += 1
        if tree is not None and folder.types:
            folder.tree = tree
            folder.scanned_types = types
            folder.scanned = time.time()
            self._save_cache()
        with self.lock:
            folder.busy = folder in self.queue
        if self.total_jobs:
            self.progress.set_fraction(min(1.0, self.done_jobs / self.total_jobs))
        self.refresh_tree()
        self.rebuild_soon()
        return GLib.SOURCE_REMOVE

    def _scan_finished(self, cancelled):
        with self.lock:
            if self.scanning:
                return GLib.SOURCE_REMOVE  # a new scan already started
            for f in self.folders:
                f.busy = False
        self.btn_scan.label.set_text("Rescan all")
        self.btn_scan.image.set_from_icon_name("view-refresh-symbolic")
        self.progress.set_visible(False)
        if cancelled:
            self.status_label.set_text("Scan stopped. Showing previous cache.")
        else:
            self._show_cache_time()
        self.refresh_tree()
        self.rebuild_soon()
        return GLib.SOURCE_REMOVE


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID, flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window or MainWindow(self)
        win.present()


def main():
    GLib.set_application_name(TITLE)
    GLib.set_prgname("file-library")
    return App().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
