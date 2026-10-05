# CLAUDE.md

This project was created and tested with the help of Claude (claude.ai), an AI
assistant made by Anthropic.

## What Claude did

- Designed the user interface together with the project owner. Every UI change started as an interactive
  mockup, and the build followed once the owner had approved it.
- Wrote the application code, the app icon, the desktop entry, the Debian packaging and the documentation
  (`README.md`, `RELEASE_NOTES.md`).
- Drew the illustration `docs/screenshot.png` with a script.
- Prepared the releases: the `.deb`, the source zip and git patches. Claude could not reach GitHub from its
  sandbox, so the project owner pushed the code and published the releases.

## How it was tested

- There is no automated test suite in this repository yet.
- The core logic in `src/file_library_core.py` was checked during development with throwaway Python scripts:
  scanning for the four file types (including `.cbz` and `.cbr`), name search with the case-sensitive and
  ignore-delimiter options, saving and loading the config and the window state (including configs from older
  versions and folders without a file type), the text export format and cancelling a scan.
- The incremental update of the file list when a folder is hidden or shown was tested against a stand-in for
  the GTK list model, not against the real widget.
- The GTK 4 window itself could not be started in Claude's sandbox because GTK 4 was not installed there.
  `src/file_library.py` was only checked for syntax, so Claude has not seen these parts run: the folder
  buttons, the context menus, the keyboard shortcuts, the About window, the green type filter, restoring the
  window layout and the scan indicator. Please check the interface on a real Ubuntu desktop and report
  anything that looks off.
- The `.deb` was built with `./build-deb.sh` and its contents and metadata were inspected with `dpkg-deb`.
  It was not installed in Claude's sandbox.
- `docs/screenshot.png` is an illustration drawn by `tools/render_screenshot.py` from sample data. It is not
  a capture of the running app.

## Notes for working on this code with Claude

- `src/file_library_core.py` has no GUI imports. Put logic there and keep `src/file_library.py` thin, so the
  logic can be tried without GTK.
- **Save config** (F7) is the only thing that writes `~/.config/file-library/config.json`: the folders,
  whether they are hidden, their file types, **Case sensitive**, **Ignore delimiter** and the **Show**
  filter. Unsaved changes are shown by a dot in the title bar, an "Unsaved changes" label and a highlighted
  button, and are dropped on restart. The window layout (`window.json`) and the scan cache (`cache.json`)
  are saved automatically. Keep it that way.
- Keep `load_config` / `save_config` backward compatible. Configs written by older versions must still load,
  with defaults for missing keys. An empty file type list for a folder is valid: such a folder is not scanned.
- The version is defined in two places: `packaging/control` and `__version__` in
  `src/file_library_core.py`. `build-deb.sh` stops if they differ. When you bump it, also update the install
  and build lines in `README.md` and the heading in `RELEASE_NOTES.md`.
- Keyboard shortcuts are defined once, in the `SHORTCUTS` list in `src/file_library.py`. The accelerators and
  the Shortcuts tab of the About window both read it. When you change it, also update the shortcut table in
  `README.md` and `RELEASE_NOTES.md`, the hint line under the file list, the toolbar tooltips and the hint
  text in `tools/render_screenshot.py`.
- File types live in `TYPES` and `TYPE_ORDER` in the core. Update the file types table in `README.md` when
  you add extensions or a type.
- The icon is generated: `tools/render_icons.py` writes the SVG and all PNG sizes from one card list, and
  `ICON_SCALE` sets how large it is on the canvas. Don't edit the generated files by hand.
- After UI changes, re-render the illustration with `python3 tools/render_screenshot.py` so it keeps matching
  the real layout. Both tools need Pillow (`python3-pil`).
- For UI changes, show the owner an interactive mockup first and build only after approval.
- Don't commit downloads (`.deb`, `.zip`, `.patch`) or the `build/` folder. `.gitignore` covers them.

Licensed under the MIT license (see `LICENSE`).
