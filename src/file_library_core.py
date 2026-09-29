"""Core logic for File Library: scanning, config, cache and text export.

Contains no GUI code so it can be tested on its own.
"""
import json
import os
import tempfile

__version__ = "1.0.5"
APP_NAME = "File Library"
COMMENTS = "Browse and search videos, images and documents from several folders."
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
                               ".xlsx", ".ods", ".csv", ".ppt", ".pptx", ".odp", ".epub"}),
}
TYPE_ORDER = ["v", "i", "d"]
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
def load_config(path=None):
    """Return a list of dicts: {path, enabled, types}."""
    data = _read_json(path or config_path(), {})
    out = []
    for item in data.get("folders", []):
        p = item.get("path")
        types = [t for t in item.get("types", []) if t in TYPES] or ["v"]
        if p:
            out.append({"path": p, "enabled": bool(item.get("enabled", True)), "types": types})
    return out


def save_config(folders, path=None):
    data = {"version": 1, "folders": [
        {"path": f["path"], "enabled": f["enabled"], "types": sorted(f["types"])} for f in folders]}
    _write_json(path or config_path(), data)


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
def _match(name, query, case_sensitive):
    if not query:
        return True
    return query in name if case_sensitive else query.lower() in name.lower()


def filter_tree(node, types, query="", case_sensitive=False):
    """Return a filtered copy of node, or None if nothing matches."""
    files = [f for f in node["files"] if f[1] in types and _match(f[0], query, case_sensitive)]
    dirs = [d for d in (filter_tree(c, types, query, case_sensitive) for c in node["dirs"]) if d]
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
