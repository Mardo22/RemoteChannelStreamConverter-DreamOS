#!/bin/sh
# Builds the DreamOS package from src/ (needs dpkg-deb, e.g. on the Dreambox itself or on Linux).
set -e
cd "$(dirname "$0")"
VERSION=$(sed -n 's/^Version: //p' src/DEBIAN/control)
OUT="release/enigma2-plugins-remotechannelconverter-dreamos_${VERSION}_all.deb"
TMP=$(mktemp -d)
cp -r src/. "$TMP/"
find "$TMP" -name '*.pyc' -o -name '*.pyo' | xargs rm -f
find "$TMP" -type d -exec chmod 755 {} \;
find "$TMP/usr" -type f -exec chmod 644 {} \;
mkdir -p release
dpkg-deb -Zgzip --root-owner-group --build "$TMP" "$OUT" 2>/dev/null || dpkg-deb -Zgzip --build "$TMP" "$OUT"
rm -rf "$TMP"
echo "built $OUT"
