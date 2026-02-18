#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Installing gcal-desktop..."

# Install the main script to /usr/local/bin
echo "  -> Copying gcal_desktop.py to /usr/local/bin/gcal-desktop"
sudo install -m 755 "${SCRIPT_DIR}/gcal_desktop.py" /usr/local/bin/gcal-desktop

# Install the autostart .desktop entry
AUTOSTART_DIR="${HOME}/.config/autostart"
mkdir -p "${AUTOSTART_DIR}"
echo "  -> Copying gcal-desktop.desktop to ${AUTOSTART_DIR}/"
cp "${SCRIPT_DIR}/gcal-desktop.desktop" "${AUTOSTART_DIR}/gcal-desktop.desktop"

echo ""
echo "Installation complete."
echo ""
echo "----------------------------------------------------------------------"
echo "Required dependencies"
echo "----------------------------------------------------------------------"
echo "Make sure the following packages are installed before running:"
echo ""
echo "  sudo apt install \\"
echo "      python3-gi \\"
echo "      gir1.2-gtk-4.0 \\"
echo "      gir1.2-webkit-6.0 \\"
echo "      gir1.2-gtk4layershell-1.0 \\"
echo "      libgtk4-layer-shell0"
echo ""
echo "Note: On older distributions that do not yet ship gir1.2-webkit-6.0,"
echo "try gir1.2-webkit2-4.1 as a fallback (results may vary)."
echo ""
echo "----------------------------------------------------------------------"
echo "Usage"
echo "----------------------------------------------------------------------"
echo "  gcal-desktop [--url URL] [--layer LAYER] [--monitor N]"
echo ""
echo "gcal-desktop will start automatically at next login via the autostart"
echo "entry placed in ${AUTOSTART_DIR}/."
echo "To start it immediately, run:  gcal-desktop &"
echo "----------------------------------------------------------------------"
