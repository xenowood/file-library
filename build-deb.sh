#!/bin/sh
# Builds file-library_<version>_all.deb from this source tree. Needs dpkg-deb.
set -e
cd "$(dirname "$0")"
VERSION=$(grep '^Version:' packaging/control | cut -d' ' -f2)
PKG="build/file-library_${VERSION}_all"

rm -rf build
mkdir -p "$PKG/DEBIAN" "$PKG/usr/bin" "$PKG/usr/lib/file-library" \
         "$PKG/usr/share/applications" "$PKG/usr/share/icons"

install -m 755 bin/file-library "$PKG/usr/bin/file-library"
install -m 644 src/file_library.py src/file_library_core.py "$PKG/usr/lib/file-library/"
install -m 644 data/org.filelibrary.FileLibrary.desktop "$PKG/usr/share/applications/"
cp -r data/icons/hicolor "$PKG/usr/share/icons/"

install -m 755 packaging/postinst packaging/postrm "$PKG/DEBIAN/"
cp packaging/control "$PKG/DEBIAN/control"
echo "Installed-Size: $(du -sk "$PKG/usr" | cut -f1)" >> "$PKG/DEBIAN/control"

find "$PKG" -type d -exec chmod 755 {} +
find "$PKG/usr" -type f ! -path "*/usr/bin/*" -exec chmod 644 {} +

dpkg-deb --build --root-owner-group "$PKG" "build/file-library_${VERSION}_all.deb"
echo "Built build/file-library_${VERSION}_all.deb"
