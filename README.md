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
- **File actions** from the right-click menu or the keyboard: copy the path or the file name, open the folder, select the file in the file manager
- **Export** the shown list as a plain `.txt` file
- Your layout and settings are remembered, and you decide when to save them

## Requirements

- Ubuntu 26.04 (any system with Python 3.10+ and GTK 4.10+ should work)
- `python3-gi` and `gir1.2-gtk-4.0`, which the `.deb` installs for you

## Install

Download `file-library_1.0.15_all.deb` from the [Releases](../../releases) page, then:

```bash
sudo apt install ./file-library_1.0.15_all.deb
```

Start **File Library** from the app grid, or run `file-library` in a terminal.

## Quick start

1. Click **Add folder** and pick a folder. No file type is selected yet, so nothing is scanned.
2. On the folder entry, switch on the **Videos / Images / Documents / Music** buttons you want. The first one you select starts the scan, and the folder is rescanned whenever you change them.
3. Type in the search box to filter the list by file name.
4. Right-click a file, or select it and use a shortcut, to copy its path or find it in your file manager.
5. Press **Save config** (F7) to keep your folders, their file types and hidden state for the next start. The search options and the **Show** filter are remembered automatically.

## Features

### Folders and file types

- Each source folder has its own set of file types. A new folder starts with none selected and is only scanned once you select its first type. A folder with no type selected is not scanned and shows no files.
- The plain icon buttons on each folder entry hide its files from the list (the eye), rescan it or remove it. The eye shows a crossed-out eye while the folder is hidden and turns orange when a hidden folder is being scanned.
- **Rescan all** (F5) scans every folder, including hidden ones. A running scan shows a progress bar, a spinner on the folder being scanned and a **Stop scan** button. Folders you rescan while another scan is running wait in a queue.

### Search

- The search looks at the file name **without its extension**.
- **Case sensitive** switches between exact and case-insensitive matching.
- **Ignore delimiter** ignores spaces, dots, commas, dashes, em dashes (`—`) and underscores. A search for `the time has come` then also finds `the.time.has.come`, `the,time,has,come`, `the-time-has-come` and `the_time_has_come`.
- **Ignore special chars** ignores the characters ``! " % & ( ) [ ] { } ? # ' =``. A search for `movie 2020 1080p` then finds `Movie (2020) [1080p].mp4`. Hover the two options to see the characters.
- Matches are highlighted in the list.

### The file list

- Folders are shown by name, files with their size in MB. Hover a folder or file to see its full path.
- The **Show** buttons at the bottom right of the list show or hide videos, images, documents and music. Selected types are green, as they are on the folder entries. At least one type stays selected.
- Right-click a file for **Open containing folder**, **Select file in manager**, **Copy file path** or **Copy file name** (the name without its extension). **Select file in manager** opens your file manager with the file selected.
- Right-click a folder and choose **Collapse folder** to collapse it together with everything below it. Its parent folder stays open.
- **Export list** (F6) saves the currently shown list, with the search and filters applied, as a `.txt` file.

### Settings and what is remembered

| What | When it is saved |
|------|------------------|
| Folders, hidden folders, file types per folder | Only when you press **Save config** |
| **Case sensitive**, **Ignore delimiter**, **Ignore special chars**, the **Show** filter | Immediately when you change them |
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
| F4  | Copy the file name without its extension |
| F5  | Rescan all folders |
| F6  | Export the shown list as a `.txt` file |
| F7  | Save config |

F1 to F4 work on the file that is selected in the list.

## File types

| Type      | Extensions                                                                    |
|-----------|-------------------------------------------------------------------------------|
| Videos    | mp4, m4v, mkv, avi, mov, wmv, flv, webm, mpg, mpeg, m2ts, mts, 3gp, ogv, vob  |
| Images    | jpg, jpeg, png, gif, webp, bmp, tif, tiff, heic, heif, svg                    |
| Documents | pdf, doc, docx, odt, rtf, txt, md, xls, xlsx, ods, csv, ppt, pptx, odp, epub, cbz, cbr |
| Music     | mp3, flac, ogg, oga, opus, wav, m4a, aac, wma, aiff, aif, ape                 |

You can change the lists in `src/file_library_core.py`.

## Files the app writes

| File | Purpose |
|------|---------|
| `~/.config/file-library/config.json` | Folders, hidden state and file types, written by **Save config** |
| `~/.config/file-library/view.json`   | Search options and the **Show** filter, written immediately |
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
sudo apt install ./build/file-library_1.0.15_all.deb
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
CLAUDE.md                  how the project was made and tested with Claude, and notes for working on it
build-deb.sh               assembles the .deb
```

## License

Released under the [MIT License](LICENSE).
