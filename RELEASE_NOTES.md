## File Library 1.0.14

- New right-click entry **Copy file name** (F4) copies the file name without its extension. The right-click menu is now ordered Open containing folder (F1), Select file in manager (F2), Copy file path (F3), Copy file name (F4).
- Right-click a folder and choose **Collapse folder** to collapse it and everything below it, without collapsing its parent.
- Fixed: the show/hide eye button reacted with a delay of several seconds on large libraries. The icon now switches at once, and only the affected folder is updated in the list.
- The app and dock icon is 10% smaller.
- New folders no longer have a file type pre-selected. The scan starts when you select the first type.
- The right-click menu shows the shortcut next to each file entry.
- **Documents** now also include comic book archives (`.cbz` and `.cbr`).
- **Music** is now a fourth file type for source folders, next to videos, images and documents.
- New **Show** buttons at the bottom right of the file list show or hide videos, images, documents and music. Selected types are green, in the list and in the folder entries.
- **Case sensitive**, **Ignore delimiter** and the Show filter are stored with **Save config**.
- The **About** window has tabs for About, Shortcuts and License.
- **Export .txt** is now called **Export list**.
- New icon with a music card: a fan of four cards (video, music, image, document) on a light grey background.
- New right-click entry **Select file in manager**, which opens the file manager with the file selected. **Open containing folder** now just opens the folder.
- The README shows an illustration of the main window. The image is also installed with the package in `/usr/share/doc/file-library/screenshot.png`.
- New eye button on each folder entry, left of the rescan button, hides its files from the list. It is a plain icon like rescan and remove, without background or frame, and turns orange while a hidden folder is being scanned. It replaces the old checkbox.

### Shortcuts

| Key | Action |
|-----|--------|
| F1  | Open containing folder |
| F2  | Select file in manager |
| F3  | Copy file path |
| F4  | Copy file name |
| F5  | Rescan all |
| F6  | Export list |
| F7  | Save config |
