#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SYSTEMD_USER_DIR="${HOME}/.config/systemd/user"
AUTOSTART_DIR="${HOME}/.config/autostart"

# --- Uninstall mode ---
if [[ "${1:-}" == "--uninstall" ]]; then
    echo "Uninstalling gcal-desktop..."
    echo ""

    # Stop and disable systemd service
    if systemctl --user is-enabled gcal-desktop.service &>/dev/null; then
        echo "  -> Stopping and disabling systemd user service"
        systemctl --user disable --now gcal-desktop.service 2>/dev/null || true
    fi

    # Remove systemd service file
    if [[ -f "${SYSTEMD_USER_DIR}/gcal-desktop.service" ]]; then
        echo "  -> Removing ${SYSTEMD_USER_DIR}/gcal-desktop.service"
        rm -f "${SYSTEMD_USER_DIR}/gcal-desktop.service"
        systemctl --user daemon-reload 2>/dev/null || true
    fi

    # Remove autostart entry
    if [[ -f "${AUTOSTART_DIR}/gcal-desktop.desktop" ]]; then
        echo "  -> Removing ${AUTOSTART_DIR}/gcal-desktop.desktop"
        rm -f "${AUTOSTART_DIR}/gcal-desktop.desktop"
    fi

    # Remove the binary
    if [[ -f /usr/local/bin/gcal-desktop ]]; then
        echo "  -> Removing /usr/local/bin/gcal-desktop"
        sudo rm -f /usr/local/bin/gcal-desktop
    fi

    echo ""
    echo "Uninstall complete."
    echo "User data remains in ~/.local/share/gcal-desktop and ~/.cache/gcal-desktop."
    echo "Remove those manually if you want a clean slate."
    exit 0
fi

# --- Install ---
echo "Installing gcal-desktop..."
echo ""

# Install the main script to /usr/local/bin
echo "  -> Copying gcal_desktop.py to /usr/local/bin/gcal-desktop"
sudo install -m 755 "${SCRIPT_DIR}/gcal_desktop.py" /usr/local/bin/gcal-desktop

# Install the systemd user service file
mkdir -p "${SYSTEMD_USER_DIR}"
echo "  -> Copying gcal-desktop.service to ${SYSTEMD_USER_DIR}/"
cp "${SCRIPT_DIR}/gcal-desktop.service" "${SYSTEMD_USER_DIR}/gcal-desktop.service"
systemctl --user daemon-reload

echo ""
echo "Installation complete."
echo ""

# --- Choose startup method ---
echo "----------------------------------------------------------------------"
echo "How should gcal-desktop start automatically?"
echo "----------------------------------------------------------------------"
echo ""
echo "  1) systemd user service  (recommended)"
echo "     Managed via systemctl. Supports restart-on-failure, logging via"
echo "     journalctl, and clean stop/start."
echo ""
echo "  2) XDG autostart (.desktop entry)"
echo "     Traditional method. The desktop environment launches the app at"
echo "     login. No automatic restart on failure."
echo ""
echo "  3) Skip (do not configure autostart)"
echo ""
read -rp "Choose [1/2/3] (default: 1): " choice
choice="${choice:-1}"

case "${choice}" in
    1)
        echo ""
        echo "  -> Enabling and starting systemd user service"
        systemctl --user enable --now gcal-desktop.service
        echo ""
        echo "gcal-desktop is now running as a systemd user service."
        echo ""
        echo "Useful commands:"
        echo "  systemctl --user status gcal-desktop"
        echo "  systemctl --user restart gcal-desktop"
        echo "  systemctl --user stop gcal-desktop"
        echo "  journalctl --user -u gcal-desktop -f"
        ;;
    2)
        mkdir -p "${AUTOSTART_DIR}"
        echo "  -> Copying gcal-desktop.desktop to ${AUTOSTART_DIR}/"
        cp "${SCRIPT_DIR}/gcal-desktop.desktop" "${AUTOSTART_DIR}/gcal-desktop.desktop"
        echo ""
        echo "gcal-desktop will start automatically at next login."
        echo "To start it now:  gcal-desktop &"
        ;;
    3)
        echo ""
        echo "Skipped. You can start gcal-desktop manually:"
        echo "  gcal-desktop &"
        echo ""
        echo "Or enable the systemd service later:"
        echo "  systemctl --user enable --now gcal-desktop.service"
        ;;
    *)
        echo "Invalid choice. Skipping autostart configuration."
        ;;
esac

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
echo "----------------------------------------------------------------------"
echo "Uninstall"
echo "----------------------------------------------------------------------"
echo "  bash install.sh --uninstall"
echo "----------------------------------------------------------------------"
