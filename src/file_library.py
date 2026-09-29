#!/usr/bin/env python3
"""File Library - GTK 4 app that lists videos, images and documents from
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
KIND_ICON = {"v": "video-x-generic", "i": "image-x-generic", "d": "x-office-document"}
CHIP_ICON = {"v": "video-x-generic-symbolic", "i": "image-x-generic-symbolic",
             "d": "x-office-document-symbolic"}
CSS = b"""
.chip { padding: 0 10px; min-height: 22px; font-size: 11px; border-radius: 11px; }
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


def highlight(name, query, case_sensitive):
    if not query:
        return esc(name)
    hay = name if case_sensitive else name.lower()
    needle = query if case_sensitive else query.lower()
    i = hay.find(needle)
    if i < 0:
        return esc(name)
    j = i + len(needle)
    return (esc(name[:i]) + '<span background="#f5d76e" foreground="#000000">'
            + esc(name[i:j]) + "</span>" + esc(name[j:]))


def fmt_size_total(size):
    mb = core.mb(size)
    return f"{mb / 1024:.2f} GB" if mb >= 1024 else f"{mb:.1f} MB"


class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=TITLE)
        self.set_default_size(1000, 680)

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

        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self._build_ui()
        self._load_state()

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
        self.btn_export = self._make_button("document-send-symbolic", "Export .txt", self.on_export)
        self.btn_about = self._make_button("help-about-symbolic", "About", self.on_about)
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
        paned.set_position(310)
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
        self.search = Gtk.SearchEntry(hexpand=True, placeholder_text="Search file names, for example garden")
        self.search.connect("search-changed", lambda *_: self.refresh_tree())
        self.case_check = Gtk.CheckButton(label="Case sensitive")
        self.case_check.connect("toggled", lambda *_: self.refresh_tree())
        search_row.append(self.search)
        search_row.append(self.case_check)
        main.append(search_row)

        self.store = Gtk.TreeStore(str, str, str, str)  # icon, markup, size, full path
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
        size_col = Gtk.TreeViewColumn()
        size_txt = Gtk.CellRendererText(xalign=1.0, xpad=8)
        size_col.pack_start(size_txt, False)
        size_col.add_attribute(size_txt, "text", 2)
        self.view.append_column(size_col)
        tree_scroll = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        tree_scroll.set_child(self.view)
        main.append(tree_scroll)
        hint = Gtk.Label(label="Right-click a file to copy its full path.", xalign=0)
        hint.add_css_class("dim-label")
        main.append(hint)
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

    # ------------------------------------------------------------ state
    def _load_state(self):
        cache = core.load_cache()
        for item in core.load_config():
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
        missing = [f for f in self.folders if f.tree is None]
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
        check = Gtk.CheckButton(active=folder.enabled, valign=Gtk.Align.START)
        check.connect("toggled", self.on_enable_toggled, folder)
        box.append(check)

        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, hexpand=True)
        name = folder.path.rstrip("/").split("/")[-1] or folder.path
        title = Gtk.Label(label=name, xalign=0, ellipsize=Pango.EllipsizeMode.END)
        path = Gtk.Label(label=folder.path, xalign=0, ellipsize=Pango.EllipsizeMode.MIDDLE)
        path.add_css_class("dim-label")
        col.append(title)
        col.append(path)
        chips = Gtk.Box(spacing=4)
        chips.set_margin_top(4)
        for key in core.TYPE_ORDER:
            chip = Gtk.ToggleButton(label=core.TYPES[key][0])
            chip.add_css_class("chip")
            chip.set_tooltip_text(core.type_hint(key))
            chip.set_active(key in folder.types)
            chip.connect("toggled", self.on_chip_toggled, folder, key)
            chips.append(chip)
        col.append(chips)
        box.append(col)

        if folder.busy:
            spinner = Gtk.Spinner(spinning=True, valign=Gtk.Align.START)
            box.append(spinner)
        remove = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        remove.add_css_class("flat")
        remove.set_valign(Gtk.Align.START)
        remove.set_tooltip_text("Remove this folder")
        remove.connect("clicked", lambda *_: GLib.idle_add(self._remove_now, folder))
        box.append(remove)
        return box

    def on_enable_toggled(self, check, folder):
        if folder.enabled == check.get_active():
            return
        folder.enabled = check.get_active()
        self.refresh_tree()
        self.set_dirty("Folder selection changed.")

    def on_chip_toggled(self, chip, folder, key):
        if chip.get_active():
            if key in folder.types:
                return
            folder.types.add(key)
        else:
            if key not in folder.types:
                return
            if len(folder.types) == 1:
                self.rebuild_soon()  # keep at least one type selected
                return
            folder.types.discard(key)
        self.set_dirty("File types changed.")
        self.start_scan([folder])

    # ------------------------------------------------------------ actions
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
        folder = Folder(path, True, {"v"})
        self.folders.append(folder)
        self.rebuild_folders()
        self.set_dirty("Folder added.")
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
        action = Gio.SimpleAction.new("copy-path", None)
        action.connect("activate", self.on_copy_path)
        self.add_action(action)
        open_action = Gio.SimpleAction.new("open-folder", None)
        open_action.connect("activate", self.on_open_folder)
        self.add_action(open_action)
        menu = Gio.Menu()
        menu.append("Copy file path", "win.copy-path")
        menu.append("Open containing folder", "win.open-folder")
        self.ctx_path = ""
        self.ctx_popover = Gtk.PopoverMenu.new_from_model(menu)
        self.ctx_popover.set_parent(self.view)
        self.ctx_popover.set_has_arrow(False)
        self.ctx_popover.set_halign(Gtk.Align.START)
        self.view.connect("destroy", lambda *_: self.ctx_popover.unparent())
        click = Gtk.GestureClick(button=3)
        click.connect("pressed", self.on_view_right_click)
        self.view.add_controller(click)

    def on_view_right_click(self, gesture, _n_press, x, y):
        bx, by = self.view.convert_widget_to_bin_window_coords(int(x), int(y))
        hit = self.view.get_path_at_pos(bx, by)
        if not hit:
            return
        tree_path = hit[0]
        full_path = self.store.get_value(self.store.get_iter(tree_path), 3)
        if not full_path:
            return  # folder rows have no file path
        self.view.get_selection().select_path(tree_path)
        self.ctx_path = full_path
        rect = Gdk.Rectangle()
        rect.x, rect.y, rect.width, rect.height = int(x), int(y), 1, 1
        self.ctx_popover.set_pointing_to(rect)
        self.ctx_popover.popup()

    def on_copy_path(self, _action, _param):
        if not self.ctx_path:
            return
        clipboard = self.get_clipboard()
        try:
            clipboard.set_text(self.ctx_path)
        except AttributeError:
            clipboard.set(self.ctx_path)
        self.show_note(f"Copied to clipboard: {self.ctx_path}")

    def on_open_folder(self, _action, _param):
        if not self.ctx_path:
            return
        folder = os.path.dirname(self.ctx_path)
        if not os.path.isdir(folder):
            self.show_note(f"Folder not found: {folder}")
            return
        try:
            # Opens the default file manager and selects the file (GTK 4.10+).
            launcher = Gtk.FileLauncher.new(Gio.File.new_for_path(self.ctx_path))
            launcher.open_containing_folder(self, None, self._on_folder_opened, folder)
        except (AttributeError, TypeError):
            self._open_folder_fallback(folder)

    def _on_folder_opened(self, launcher, result, folder):
        try:
            launcher.open_containing_folder_finish(result)
        except GLib.Error:
            self._open_folder_fallback(folder)
            return
        self.show_note(f"Opened folder: {folder}")

    def _open_folder_fallback(self, folder):
        try:
            uri = Gio.File.new_for_path(folder).get_uri()
            Gio.AppInfo.launch_default_for_uri(uri, None)
        except GLib.Error as err:
            self.show_note(f"Couldn't open the folder: {err.message}")
            return
        self.show_note(f"Opened folder: {folder}")

    def on_save(self):
        if not self.dirty:
            self.show_note("Nothing to save. The config is up to date.")
            return
        try:
            core.save_config([{"path": f.path, "enabled": f.enabled, "types": f.types}
                              for f in self.folders])
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
        dialog = Gtk.AboutDialog(transient_for=self, modal=True)
        dialog.set_program_name(core.APP_NAME)
        dialog.set_version(core.__version__)
        dialog.set_comments(core.COMMENTS)
        dialog.set_logo_icon_name("file-library")
        dialog.set_website(core.REPO_URL)
        dialog.set_website_label(core.REPO_URL.replace("https://", ""))
        dialog.set_copyright(core.COPYRIGHT)
        dialog.set_license_type(Gtk.License.CUSTOM)
        dialog.set_license(core.LICENSE_TEXT)
        dialog.set_wrap_license(True)
        dialog.present()

    # ------------------------------------------------------------ list view
    def visible_roots(self):
        query = self.search.get_text()
        case = self.case_check.get_active()
        roots = []
        for f in self.folders:
            if f.enabled and f.tree is not None:
                node = core.filter_tree(f.tree, f.types, query, case)
                if node is not None:
                    roots.append((f.path, node))
        return roots

    def refresh_tree(self):
        query = self.search.get_text()
        case = self.case_check.get_active()
        self.store.clear()
        count, size = 0, 0
        for path, node in self.visible_roots():
            it = self.store.append(None, ["folder", f"<b>{esc(path)}</b>", "", ""])
            self._fill(it, node, query, case, path)
            n, s = core.count_tree(node)
            count, size = count + n, size + s
        self.view.expand_all()
        self.count_label.set_text(f"{count} files \u00b7 {fmt_size_total(size)} shown")

    def _fill(self, parent, node, query, case, base):
        for name, kind, nbytes in node["files"]:
            self.store.append(parent, [KIND_ICON[kind], highlight(name, query, case),
                                       f"{core.mb(nbytes):.2f} MB", os.path.join(base, name)])
        for sub in node["dirs"]:
            it = self.store.append(parent, ["folder", f"<b>{esc(sub['name'])}</b>", "", ""])
            self._fill(it, sub, query, case, os.path.join(base, sub["name"]))

    # ------------------------------------------------------------ scanning
    def on_scan_clicked(self):
        if self.scanning:
            self.cancel.set()
            return
        if not self.folders:
            self.show_note("Add a folder first.")
            return
        self.start_scan(list(self.folders))

    def start_scan(self, folders):
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
        if tree is not None:
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
