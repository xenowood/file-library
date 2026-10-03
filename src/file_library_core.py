"""Core logic for File Library: scanning, config, cache and text export.

Contains no GUI code so it can be tested on its own.
"""
import json
import os
import tempfile

__version__ = "1.0.14"
APP_NAME = "File Library"
COMMENTS = "Browse and search videos, images, documents and music from several folders."
REPO_URL = "https://github.com/xenowood/file-library"
COPYRIGHT = "Copyright \u00a9 2026 xenowood"
LICENSE_TEXT = """MIT License

Copyright (c) 2026 xenowood

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

TYPES = {
    "v": ("Videos", "🎬", {".mp4", ".m4v", ".mkv", ".avi", ".mov", ".wmv", ".flv", ".webm",
                            ".mpg", ".mpeg", ".m2ts", ".mts", ".3gp", ".ogv", ".vob"}),
    "i": ("Images", "📷", {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tif", ".tiff",
                            ".heic", ".heif", ".svg"}),
    "d": ("Documents", "📄", {".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".xls",
                               ".xlsx", ".ods", ".csv", ".ppt", ".pptx", ".odp", ".epub", ".cbz", ".cbr"}),
    "m": ("Music", "🎵", {".mp3", ".flac", ".ogg", ".oga", ".opus", ".wav", ".m4a", ".aac",
                           ".wma", ".aiff", ".aif", ".ape"}),
}
TYPE_ORDER = ["v", "i", "d", "m"]
EXT_TO_TYPE = {ext: key for key, (_, _, exts) in TYPES.items() for ext in exts}


def type_hint(key):
    return ", ".join(sorted(e.lstrip(".") for e in TYPES[key][2]))


# ---------------------------------------------------------------- paths
def config_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "file-library", "config.json")


def cache_path():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return os.path.join(base, "file-library", "cache.json")


def window_state_path():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    return os.path.join(base, "file-library", "window.json")


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def _read_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return default


# ---------------------------------------------------------------- config
def _ordered_types(keys):
    return [k for k in TYPE_ORDER if k in set(keys)]


def load_config(path=None):
    """Return the saved config as a dict.

    {"folders": [{path, enabled, types}], "case_sensitive": bool,
     "ignore_delimiter": bool, "view_types": [type keys shown in the list]}
    """
    data = _read_json(path or config_path(), {})
    folders = []
    for item in data.get("folders", []):
        p = item.get("path")
        types = [t for t in item.get("types", []) if t in TYPES]
        if p:
            folders.append({"path": p, "enabled": bool(item.get("enabled", True)), "types": types})
    search = data.get("search", {})
    view_types = _ordered_types(data.get("view_types", TYPE_ORDER)) or list(TYPE_ORDER)
    return {
        "folders": folders,
        "case_sensitive": bool(search.get("case_sensitive", False)),
        "ignore_delimiter": bool(search.get("ignore_delimiter", False)),
        "view_types": view_types,
    }


def save_config(folders, settings=None, path=None):
    """folders: list of {path, enabled, types}; settings: search options and view filter."""
    settings = settings or {}
    data = {
        "version": 2,
        "folders": [{"path": f["path"], "enabled": f["enabled"], "types": _ordered_types(f["types"])}
                    for f in folders],
        "search": {"case_sensitive": bool(settings.get("case_sensitive", False)),
                   "ignore_delimiter": bool(settings.get("ignore_delimiter", False))},
        "view_types": _ordered_types(settings.get("view_types", TYPE_ORDER)),
    }
    _write_json(path or config_path(), data)


# ---------------------------------------------------------------- window state
def load_window_state(path=None):
    """Window size, maximized flag and splitter position from the last session."""
    data = _read_json(path or window_state_path(), {})
    limits = {"width": (500, 10000), "height": (350, 10000), "paned": (120, 5000)}
    state = {"maximized": bool(data.get("maximized", False))}
    for key, (low, high) in limits.items():
        value = data.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            state[key] = max(low, min(high, value))
    return state


def save_window_state(state, path=None):
    _write_json(path or window_state_path(), state)


# ---------------------------------------------------------------- cache
def load_cache(path=None):
    return _read_json(path or cache_path(), {}).get("folders", {})


def save_cache(entries, path=None):
    _write_json(path or cache_path(), {"version": 1, "folders": entries})


# ---------------------------------------------------------------- scanning
class Cancelled(Exception):
    pass


def scan_folder(root, types, progress=None, cancel=None):
    """Scan root for files of the given type keys.

    Returns a node {"name", "files": [[name, type, bytes]], "dirs": [node]},
    or None if cancelled. Empty subfolders are dropped.
    """
    wanted = {ext: k for ext, k in EXT_TO_TYPE.items() if k in types}
    counter = [0]

    def walk(path, name):
        if cancel is not None and cancel.is_set():
            raise Cancelled
        node = {"name": name, "files": [], "dirs": []}
        try:
            entries = sorted(os.scandir(path), key=lambda e: e.name.lower())
        except OSError:
            return node
        for e in entries:
            try:
                if e.is_dir(follow_symlinks=False):
                    child = walk(e.path, e.name)
                    if child["files"] or child["dirs"]:
                        node["dirs"].append(child)
                elif e.is_file():
                    counter[0] += 1
                    if progress and counter[0] % 200 == 0:
                        progress(counter[0])
                    kind = wanted.get(os.path.splitext(e.name)[1].lower())
                    if kind:
                        node["files"].append([e.name, kind, e.stat().st_size])
            except OSError:
                continue
        return node

    try:
        result = walk(root, root)
    except Cancelled:
        return None
    if progress:
        progress(counter[0])
    return result


# ---------------------------------------------------------------- filtering
DELIMITERS = " ._-,"


def _fold(text, case_sensitive, ignore_delimiters):
    """Return (folded text, index of each folded char in the original text)."""
    chars, index = [], []
    for i, ch in enumerate(text):
        if ignore_delimiters and ch in DELIMITERS:
            continue
        for c in (ch if case_sensitive else ch.lower()):
            chars.append(c)
            index.append(i)
    return "".join(chars), index


def find_match(name, query, case_sensitive=False, ignore_delimiters=False):
    """Return (start, end) of the first match of query in name, or None.

    With ignore_delimiters, spaces, dots, commas, dashes and underscores are
    ignored on both sides, so "the time has come" also matches "the.time-has_come".
    An empty query matches everything and returns (0, 0).
    """
    wanted, _ = _fold(query, case_sensitive, ignore_delimiters)
    if not wanted:
        return (0, 0)
    haystack, index = _fold(name, case_sensitive, ignore_delimiters)
    pos = haystack.find(wanted)
    if pos < 0:
        return None
    return index[pos], index[pos + len(wanted) - 1] + 1


def find_in_filename(filename, query, case_sensitive=False, ignore_delimiters=False):
    """Like find_match, but only looks at the file name without its extension.

    The returned span is valid for the full file name too, because the name
    without extension is a prefix of it.
    """
    stem = os.path.splitext(filename)[0]
    return find_match(stem, query, case_sensitive, ignore_delimiters)


def _match(filename, query, case_sensitive, ignore_delimiters=False):
    return find_in_filename(filename, query, case_sensitive, ignore_delimiters) is not None


def filter_tree(node, types, query="", case_sensitive=False, ignore_delimiters=False):
    """Return a filtered copy of node, or None if nothing matches."""
    files = [f for f in node["files"]
             if f[1] in types and _match(f[0], query, case_sensitive, ignore_delimiters)]
    dirs = [d for d in (filter_tree(c, types, query, case_sensitive, ignore_delimiters)
                        for c in node["dirs"]) if d]
    if not files and not dirs:
        return None
    return {"name": node["name"], "files": files, "dirs": dirs}


def count_tree(node):
    n, size = len(node["files"]), sum(f[2] for f in node["files"])
    for d in node["dirs"]:
        dn, ds = count_tree(d)
        n, size = n + dn, size + ds
    return n, size


def mb(size):
    return size / (1024 * 1024)


# ---------------------------------------------------------------- export
def format_export(roots):
    """roots: list of (path, filtered_node). Returns text in the tree layout."""
    lines = []

    def emit(node, depth, root_path=None):
        if depth == 0:
            lines.append((f"📁 {root_path}", None))
        else:
            lines.append(("   " * depth + f"📁 {node['name']}", None))
        pad = "   " * (depth + 1)
        for name, kind, size in node["files"]:
            lines.append((f"{pad}{TYPES[kind][1]} {name}", mb(size)))
        for d in node["dirs"]:
            emit(d, depth + 1)

    for path, node in roots:
        emit(node, 0, path)
    width = max((len(t) for t, s in lines if s is not None), default=0) + 4
    out = [t if s is None else f"{t:<{width}}{s:.2f} MB" for t, s in lines]
    return "\n".join(out) + ("\n" if out else "")
