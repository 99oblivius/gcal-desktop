#!/usr/bin/env python3
"""gcal-desktop: Display Google Calendar as a Wayland desktop wallpaper.

Uses gtk4-layer-shell to place a WebKitGTK webview on the desktop,
sitting above the wallpaper but below normal windows. Persists
cookies so you stay logged in across restarts.
"""

from ctypes import CDLL

# gtk4-layer-shell MUST be loaded before any gi imports
CDLL("libgtk4-layer-shell.so")

import argparse
import os
import sys

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
gi.require_version("Gtk4LayerShell", "1.0")

from gi.repository import Gdk, GLib, Gtk, WebKit
from gi.repository import Gtk4LayerShell as LayerShell

APP_ID = "com.github.gcal-desktop"
DEFAULT_URL = "https://calendar.google.com"
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

LAYER_MAP = {
    "background": LayerShell.Layer.BACKGROUND,
    "bottom": LayerShell.Layer.BOTTOM,
    "top": LayerShell.Layer.TOP,
}


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="gcal-desktop",
        description="Display Google Calendar as a Wayland desktop wallpaper.",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"URL to load (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--layer",
        choices=["background", "bottom", "top"],
        default="bottom",
        help="Layer shell layer (default: bottom)",
    )
    parser.add_argument(
        "--monitor",
        type=int,
        default=None,
        help="Monitor index to display on (default: primary/all)",
    )
    parser.add_argument(
        "--service-install",
        action="store_true",
        help="Install and enable the systemd user service, then exit",
    )
    parser.add_argument(
        "--service-uninstall",
        action="store_true",
        help="Disable and remove the systemd user service, then exit",
    )
    # Separate our args from GTK args so Gtk.Application doesn't choke
    args, _remaining = parser.parse_known_args()
    return args


def build_network_session():
    """Create a persistent WebKit.NetworkSession for cookie storage."""
    data_dir = os.path.expanduser("~/.local/share/gcal-desktop")
    cache_dir = os.path.expanduser("~/.cache/gcal-desktop")
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(cache_dir, exist_ok=True)

    network_session = WebKit.NetworkSession.new(data_dir, cache_dir)

    cookie_manager = network_session.get_cookie_manager()
    cookie_manager.set_accept_policy(WebKit.CookieAcceptPolicy.ALWAYS)

    return network_session


def configure_webview_settings(webview):
    """Apply common settings to a WebView instance."""
    settings = webview.get_settings()
    settings.set_user_agent(USER_AGENT)
    settings.set_enable_javascript(True)
    settings.set_hardware_acceleration_policy(
        WebKit.HardwareAccelerationPolicy.ON_DEMAND
    )
    settings.set_enable_smooth_scrolling(True)
    settings.set_enable_developer_extras(False)


def create_popup_webview(main_webview, navigation_action, network_session):
    """Handle popup windows for Google OAuth login flow.

    Google OAuth opens popups during login. We create a regular GTK
    window (not a layer-shell window) so the user can interact with
    the login form normally.

    Returns the new WebView that WebKit will load the popup into.
    """
    popup_window = Gtk.Window(
        title="Google Sign-In",
        default_width=500,
        default_height=700,
    )

    # Use related_view so the popup shares the same process and session
    popup_webview = WebKit.WebView.new(
        network_session=network_session,
        related_view=main_webview,
    )
    configure_webview_settings(popup_webview)

    # Close the popup window when the webview signals it should close
    popup_webview.connect("close", lambda wv: popup_window.close())

    # Also update window title to match page title
    popup_webview.connect(
        "notify::title",
        lambda wv, _param: popup_window.set_title(wv.get_title() or "Google Sign-In"),
    )

    popup_window.set_child(popup_webview)

    # Realize the window before returning so the webview has a surface
    popup_window.present()

    return popup_webview


def _on_create_safe(main_webview, navigation_action, network_session):
    """Wrapper around popup creation that handles errors gracefully."""
    try:
        return create_popup_webview(main_webview, navigation_action, network_session)
    except Exception as exc:
        print(f"Warning: failed to create popup window: {exc}", file=sys.stderr)
        # Fall back: load the popup URL in the main webview instead
        uri = navigation_action.get_request().get_uri()
        if uri:
            main_webview.load_uri(uri)
        return None


class GcalDesktopApp(Gtk.Application):
    """Main application class."""

    def __init__(self, args):
        super().__init__(application_id=APP_ID)
        self.args = args
        self.network_session = None

    def do_activate(self):
        """Create and present the main layer-shell window."""
        self.network_session = build_network_session()

        window = Gtk.ApplicationWindow(application=self)

        # --- Layer shell configuration ---
        LayerShell.init_for_window(window)
        LayerShell.set_layer(window, LAYER_MAP[self.args.layer])

        # Anchor all four edges so the window fills the screen
        LayerShell.set_anchor(window, LayerShell.Edge.TOP, True)
        LayerShell.set_anchor(window, LayerShell.Edge.BOTTOM, True)
        LayerShell.set_anchor(window, LayerShell.Edge.LEFT, True)
        LayerShell.set_anchor(window, LayerShell.Edge.RIGHT, True)

        # -1 means do not reserve space; overlap everything on this layer
        LayerShell.set_exclusive_zone(window, -1)

        # Allow keyboard focus when the user clicks
        LayerShell.set_keyboard_mode(
            window, LayerShell.KeyboardMode.ON_DEMAND
        )

        # Pin to a specific monitor if requested
        if self.args.monitor is not None:
            display = Gdk.Display.get_default()
            if display is not None:
                monitors = display.get_monitors()
                if 0 <= self.args.monitor < monitors.get_n_items():
                    monitor = monitors.get_item(self.args.monitor)
                    LayerShell.set_monitor(window, monitor)
                else:
                    print(
                        f"Warning: monitor index {self.args.monitor} out of "
                        f"range (0-{monitors.get_n_items() - 1}). "
                        "Using default.",
                        file=sys.stderr,
                    )

        # --- WebView ---
        webview = WebKit.WebView(network_session=self.network_session)
        configure_webview_settings(webview)

        # Expand to fill the window
        webview.set_hexpand(True)
        webview.set_vexpand(True)

        # Handle popups (Google OAuth login windows)
        network_session = self.network_session
        webview.connect(
            "create",
            lambda wv, nav: _on_create_safe(wv, nav, network_session),
        )

        window.set_child(webview)
        window.present()

        # Load the target URL
        webview.load_uri(self.args.url)


def _find_service_source():
    """Locate the .service file shipped alongside this script."""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "gcal-desktop.service"),
        "/usr/lib/systemd/user/gcal-desktop.service",
        "/usr/local/lib/systemd/user/gcal-desktop.service",
    ]
    for path in candidates:
        if os.path.isfile(path):
            return path
    return None


def _service_install():
    """Install and enable the systemd user service."""
    import shutil
    import subprocess

    service_dir = os.path.expanduser("~/.config/systemd/user")
    service_dest = os.path.join(service_dir, "gcal-desktop.service")

    source = _find_service_source()
    if source is None:
        print("Error: cannot find gcal-desktop.service file.", file=sys.stderr)
        print("Make sure it exists next to gcal_desktop.py or in /usr/lib/systemd/user/.", file=sys.stderr)
        return 1

    os.makedirs(service_dir, exist_ok=True)
    shutil.copy2(source, service_dest)
    print(f"Installed service file to {service_dest}")

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=True)
    subprocess.run(["systemctl", "--user", "enable", "gcal-desktop.service"], check=True)
    print("Service enabled. Start it with:")
    print("  systemctl --user start gcal-desktop.service")
    return 0


def _service_uninstall():
    """Disable and remove the systemd user service."""
    import subprocess

    service_path = os.path.expanduser("~/.config/systemd/user/gcal-desktop.service")

    # Best-effort stop and disable
    subprocess.run(
        ["systemctl", "--user", "disable", "--now", "gcal-desktop.service"],
        stderr=subprocess.DEVNULL,
    )

    if os.path.isfile(service_path):
        os.remove(service_path)
        print(f"Removed {service_path}")
    else:
        print(f"Service file not found at {service_path}, nothing to remove.")

    subprocess.run(["systemctl", "--user", "daemon-reload"], check=False)
    print("Service disabled and removed.")
    return 0


def main():
    args = parse_args()

    if args.service_install:
        return _service_install()
    if args.service_uninstall:
        return _service_uninstall()

    app = GcalDesktopApp(args)
    return app.run(sys.argv[:1])  # pass only argv[0] to GTK


if __name__ == "__main__":
    raise SystemExit(main())
