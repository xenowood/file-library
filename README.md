# File Library

File Library is a desktop app for Ubuntu that keeps an index of the videos, images, documents and music spread across your folders. Add one or more source folders, choose which file types to index in each of them, and browse everything in one tree with file sizes in MB.

The scan result is cached, so searching is instant and the app only rescans when you ask it to. You can search by file name, ignore delimiters such as dots and underscores, copy a file's full path, jump to it in your file manager and export the list as a text file.

<p align="center">
  <img src="docs/screenshot.png" alt="File Library main window with four folders, one per file type, and a list of videos, images, documents and music" width="900">
</p>
<p align="center"><em>Illustration of the main window: four folders, one per file type, and the combined file list.</em></p>

## Highlights

- **Several source folders**, each with its own file types: videos, images, documents and music
- **Cached index** with a scan indicator, so searches never wait for a rescan
- **Search that skips the clutter**: file names only, case sensitive or not, with or without delimiters
- **Show and hide** folders and file types without losing your setup
- **File actions** from the right-click menu or the keyboard: copy the path, open the folder, select the file in the file manager
- **Export** the shown list as a plain `.txt` file
- Your layout and settings are remembered, and you decide when to save them

## Requirements

- Ubuntu 26.04 (any system with Python 3.10+ and GTK 4.10+ should work)
- `python3-gi` and `gir1.2-gtk-4.0`, which the `.deb` installs for you

## Install

Download `file-library_1.0.9_all.deb` from the [Releases](../../releases) page, then:

```bash
sudo apt install ./file-library_1.0.9_all.deb
```

Start **File Library** from the app grid, or run `file-library` in a terminal.

## Quick start

1. Click **Add folder** and pick a folder. New folders start with **Videos** selected, and the folder is scanned right away.
2. On the folder entry, switch the **Videos / Images / Documents / Music** buttons to choose what gets indexed. The folder is rescanned when you change them.
3. Type in the search box to filter the list by file name.
4. Right-click a file, or select it and use a shortcut, to copy its path or find it in your file manager.
5. Press **Save config** (F7) to keep your folders and settings for the next start.

## Features

### Folders and file types

- Each source folder has its own set of file types. At least one type stays selected.
- The buttons on each folder entry hide its files from the list (the eye button), rescan it or remove it. The eye icon shows a crossed-out eye while the folder is hidden and turns orange when a hidden folder is being scanned.
- **Rescan all** (F5) scans every folder, including hidden ones. A running scan shows a progress bar, a spinner on the folder being scanned and a **Stop scan** button. Folders you rescan while another scan is running wait in a queue.

### Search

- The search looks at the file name **without its extension**.
- **Case sensitive** switches between exact and case-insensitive matching.
- **Ignore delimiter** treats spaces, dots, commas, dashes and underscores as equal and ignores them. A search for `the time has come` then also finds `the.time.has.come`, `the,time,has,come`, `the-time-has-come` and `the_time_has_come`.
- Matches are highlighted in the list.

### The file list

- Folders are shown by name, files with their size in MB. Hover a folder or file to see its full path.
- The **Show** buttons at the bottom right of the list show or hide videos, images, documents and music. Selected types are green, as they are on the folder entries. At least one type stays selected.
- Right-click a file for **Copy file path**, **Open containing folder** or **Select file in manager**. The last one opens your file manager with the file selected.
- **Export list** (F6) saves the currently shown list, with the search and filters applied, as a `.txt` file.

### Settings and what is remembered

| What | When it is saved |
|------|------------------|
| Folders, hidden folders, file types per folder, **Case sensitive**, **Ignore delimiter**, the **Show** filter | Only when you press **Save config** |
| Window size, maximized state, position of the divider | Automatically when the window closes |
| The scanned file index | Automatically after every scan |

Unsaved changes are marked by a dot in the title bar, an "Unsaved changes" label in the status bar and a highlighted **Save config** button. If you restart without saving, they are dropped, so you can try things out freely.

## Keyboard shortcuts

The same list is shown in **About**, tab **Shortcuts**.

| Key | Action |
|-----|--------|
| F1  | Open the folder that contains the selected file |
| F2  | Select the file in the file manager |
| F3  | Copy the full path of the selected file |
| F5  | Rescan all folders |
| F6  | Export the shown list as a `.txt` file |
| F7  | Save config |

F1, F2 and F3 work on the file that is selected in the list.

## File types

| Type      | Extensions                                                                    |
|-----------|-------------------------------------------------------------------------------|
| Videos    | mp4, m4v, mkv, avi, mov, wmv, flv, webm, mpg, mpeg, m2ts, mts, 3gp, ogv, vob  |
| Images    | jpg, jpeg, png, gif, webp, bmp, tif, tiff, heic, heif, svg                    |
| Documents | pdf, doc, docx, odt, rtf, txt, md, xls, xlsx, ods, csv, ppt, pptx, odp, epub  |
| Music     | mp3, flac, ogg, oga, opus, wav, m4a, aac, wma, aiff, aif, ape                 |

You can change the lists in `src/file_library_core.py`.

## Files the app writes

| File | Purpose |
|------|---------|
| `~/.config/file-library/config.json` | Folders, file types, search options and the type filter, written by **Save config** |
| `~/.config/file-library/window.json` | Window size and divider position, written when the window closes |
| `~/.cache/file-library/cache.json`   | The scanned file index |

Delete these files to start from scratch.

## Run from source

```bash
sudo apt install python3 python3-gi gir1.2-gtk-4.0
python3 src/file_library.py
```

## Build the .deb

```bash
./build-deb.sh
sudo apt install ./build/file-library_1.0.9_all.deb
```

Building only needs `dpkg-deb`, which Ubuntu already includes. The version is defined in `packaging/control` and `src/file_library_core.py`, and the build stops if the two differ.

`tools/render_icons.py` and `tools/render_screenshot.py` regenerate the icons and the illustration. They need Pillow (`python3-pil`).

## Project layout

```
src/file_library.py        GTK 4 interface
src/file_library_core.py   scanning, config, cache, export, version (no GUI code)
bin/file-library           launcher script installed to /usr/bin
data/                      .desktop entry and icons (SVG and PNG sizes)
packaging/                 Debian control file, copyright and install hooks
tools/render_icons.py      renders the app icon (SVG and PNG sizes)
tools/render_screenshot.py renders docs/screenshot.png (an illustration, not a capture)
docs/screenshot.png        image shown at the top of this README
RELEASE_NOTES.md           notes for the latest GitHub release
build-deb.sh               assembles the .deb
```

## License

Released under the [MIT License](LICENSE).
