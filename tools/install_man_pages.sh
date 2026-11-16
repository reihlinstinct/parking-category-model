#!/bin/sh
# Install the shipped parking-category-model man pages (issue #26).
# Usage: tools/install_man_pages.sh [PREFIX]   (default: /usr/local)
# Installs to $DESTDIR$PREFIX/share/man/man1/ (DESTDIR for staged packaging).
# Only the shipped module commands have pages; internal CI/dev scripts
# deliberately get none.
set -eu
PREFIX=${1:-/usr/local}
SRC="$(cd "$(dirname "$0")/.." && pwd)/man/man1"
DEST="${DESTDIR:-}$PREFIX/share/man/man1"
mkdir -p "$DEST"
for page in "$SRC"/parking-category-model-*.1; do
    install -m 644 "$page" "$DEST/"
    echo "installed $DEST/$(basename "$page")"
done
