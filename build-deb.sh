#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PKG_NAME="gcal-desktop"
PKG_VERSION="1.0.0"
PKG_ARCH="all"
PKG_MAINTAINER="gcal-desktop contributors <noreply@github.com>"
PKG_DESCRIPTION="Google Calendar rendered as your desktop wallpaper on Wayland"
PKG_HOMEPAGE="https://github.com/99oblivius/gcal-desktop"
PKG_DEPENDS="python3-gi, gir1.2-gtk-4.0, gir1.2-webkit-6.0, gir1.2-gtk4layershell-1.0, libgtk4-layer-shell0"

DEB_FILENAME="${PKG_NAME}_${PKG_VERSION}_${PKG_ARCH}.deb"
BUILD_DIR="$(mktemp -d)"

cleanup() {
    rm -rf "${BUILD_DIR}"
}
trap cleanup EXIT

echo "Building ${DEB_FILENAME}..."
echo "  Build directory: ${BUILD_DIR}"

# --- Create directory structure ---
mkdir -p "${BUILD_DIR}/DEBIAN"
mkdir -p "${BUILD_DIR}/usr/bin"
mkdir -p "${BUILD_DIR}/usr/share/applications"
mkdir -p "${BUILD_DIR}/usr/lib/systemd/user"
mkdir -p "${BUILD_DIR}/usr/share/doc/${PKG_NAME}"

# --- DEBIAN/control ---
cat > "${BUILD_DIR}/DEBIAN/control" <<EOF
Package: ${PKG_NAME}
Version: ${PKG_VERSION}
Architecture: ${PKG_ARCH}
Maintainer: ${PKG_MAINTAINER}
Depends: ${PKG_DEPENDS}
Homepage: ${PKG_HOMEPAGE}
Section: utils
Priority: optional
Description: ${PKG_DESCRIPTION}
 Uses gtk4-layer-shell to place a WebKitGTK webview on the desktop,
 sitting above the wallpaper but below normal windows. Persists
 cookies so you stay logged in across restarts.
 .
 Supports Wayland compositors that implement the wlr-layer-shell
 protocol (KDE Plasma 6, Hyprland, Sway, etc.).
EOF

# --- DEBIAN/postinst ---
cat > "${BUILD_DIR}/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e

echo ""
echo "gcal-desktop has been installed."
echo ""
echo "To start it as a systemd user service:"
echo "  systemctl --user enable --now gcal-desktop.service"
echo ""
echo "Or to use autostart instead, copy the desktop entry:"
echo "  mkdir -p ~/.config/autostart"
echo "  cp /usr/share/applications/gcal-desktop.desktop ~/.config/autostart/"
echo ""

exit 0
POSTINST
chmod 0755 "${BUILD_DIR}/DEBIAN/postinst"

# --- DEBIAN/prerm ---
cat > "${BUILD_DIR}/DEBIAN/prerm" <<'PRERM'
#!/bin/sh
set -e

# Best-effort: stop and disable the service if it was enabled
if command -v systemctl >/dev/null 2>&1; then
    systemctl --user disable --now gcal-desktop.service 2>/dev/null || true
fi

# Remove autostart entry if present
rm -f "${HOME}/.config/autostart/gcal-desktop.desktop" 2>/dev/null || true

exit 0
PRERM
chmod 0755 "${BUILD_DIR}/DEBIAN/prerm"

# --- Install files ---

# Main executable
install -m 755 "${SCRIPT_DIR}/gcal_desktop.py" "${BUILD_DIR}/usr/bin/gcal-desktop"

# Desktop entry
install -m 644 "${SCRIPT_DIR}/gcal-desktop.desktop" "${BUILD_DIR}/usr/share/applications/gcal-desktop.desktop"

# Systemd user service (adjust ExecStart for system-wide install path)
sed 's|ExecStart=/usr/local/bin/gcal-desktop|ExecStart=/usr/bin/gcal-desktop|' \
    "${SCRIPT_DIR}/gcal-desktop.service" \
    > "${BUILD_DIR}/usr/lib/systemd/user/gcal-desktop.service"
chmod 644 "${BUILD_DIR}/usr/lib/systemd/user/gcal-desktop.service"

# --- Build the .deb ---
dpkg-deb --root-owner-group --build "${BUILD_DIR}" "${SCRIPT_DIR}/${DEB_FILENAME}"

echo ""
echo "Package built successfully: ${SCRIPT_DIR}/${DEB_FILENAME}"
echo ""
echo "Install with:"
echo "  sudo apt install ./${DEB_FILENAME}"
echo ""
echo "Or on older dpkg:"
echo "  sudo dpkg -i ${DEB_FILENAME} && sudo apt-get install -f"
