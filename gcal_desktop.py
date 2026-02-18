#!/usr/bin/env python3
"""gcal-desktop: Display Google Calendar as a Wayland desktop wallpaper.

Uses gtk4-layer-shell to place a WebKitGTK webview on the desktop,
sitting above the wallpaper but below normal windows. Persists
cookies so you stay logged in across restarts.
"""

import argparse
import os
import shutil
import sys


def _check_dependencies():
    """Verify runtime dependencies and print helpful errors if missing."""
    errors = []

    # Check libgtk4-layer-shell.so
    from ctypes import CDLL, util
    lib = util.find_library("gtk4-layer-shell")
    if lib:
        CDLL(lib)
    else:
        try:
            CDLL("libgtk4-layer-shell.so")
        except OSError:
            errors.append(
                "libgtk4-layer-shell is not installed.\n"
                "  Arch:   sudo pacman -S gtk4-layer-shell\n"
                "  Ubuntu: sudo apt install libgtk4-layer-shell0"
            )

    # Check Python GObject introspection
    try:
        import gi
    except ImportError:
        errors.append(
            "PyGObject (python-gi) is not installed.\n"
            "  Arch:   sudo pacman -S python-gobject\n"
            "  Ubuntu: sudo apt install python3-gi"
        )
        _die(errors)
        return  # unreachable

    # Check GI typelibs
    gi_deps = {
        ("Gdk", "4.0"): ("gtk4", "gir1.2-gtk-4.0"),
        ("Gtk", "4.0"): ("gtk4", "gir1.2-gtk-4.0"),
        ("WebKit", "6.0"): ("webkitgtk-6.0", "gir1.2-webkit-6.0"),
        ("Gtk4LayerShell", "1.0"): ("gtk4-layer-shell", "gir1.2-gtk4layershell-1.0"),
    }
    for (namespace, version), (arch_pkg, ubuntu_pkg) in gi_deps.items():
        try:
            gi.require_version(namespace, version)
        except ValueError:
            errors.append(
                f"GObject introspection data for {namespace}-{version} not found.\n"
                f"  Arch:   sudo pacman -S {arch_pkg}\n"
                f"  Ubuntu: sudo apt install {ubuntu_pkg}"
            )

    # Check GStreamer (needed by WebKitGTK for Google Calendar)
    gst_check = shutil.which("gst-inspect-1.0")
    if gst_check:
        import subprocess
        result = subprocess.run(
            ["gst-inspect-1.0", "autoaudiosink"],
            capture_output=True,
        )
        if result.returncode != 0:
            errors.append(
                "GStreamer audio plugin 'autoaudiosink' not found.\n"
                "  Arch:   sudo pacman -S gst-plugins-base gst-plugins-good\n"
                "  Ubuntu: sudo apt install gstreamer1.0-plugins-base gstreamer1.0-plugins-good"
            )

    if errors:
        _die(errors)


def _die(errors):
    """Print dependency errors and exit."""
    print("gcal-desktop: missing dependencies\n", file=sys.stderr)
    for err in errors:
        print(f"  * {err}\n", file=sys.stderr)
    sys.exit(1)


_check_dependencies()

# --- Safe to import GTK stack now ---
from ctypes import CDLL
CDLL("libgtk4-layer-shell.so")

import gi
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk", "4.0")
gi.require_version("WebKit", "6.0")
gi.require_version("Gtk4LayerShell", "1.0")

from gi.repository import Gdk, Gio, Gtk, WebKit
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
    "overlay": LayerShell.Layer.OVERLAY,
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
        choices=["background", "bottom", "top", "overlay"],
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
        "--no-layer-shell",
        action="store_true",
        help="Run as a regular window instead of a desktop layer",
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

    # Persist cookies to disk so login survives restarts
    cookie_file = os.path.join(data_dir, "cookies.sqlite")
    cookie_manager.set_persistent_storage(
        cookie_file, WebKit.CookiePersistentStorage.SQLITE
    )

    return network_session


def configure_webview_settings(webview):
    """Apply common settings to a WebView instance."""
    settings = webview.get_settings()
    settings.set_user_agent(USER_AGENT)


def _on_tls_error(webview, uri, certificate, errors, network_session):
    """Accept TLS certificates and retry the load."""
    from urllib.parse import urlparse
    host = urlparse(uri).hostname
    if host:
        network_session.allow_tls_certificate_for_host(certificate, host)
        webview.load_uri(uri)
    return True


def _on_context_menu(webview, context_menu, hit_test, _user_data):
    """Add custom items to the WebView's right-click context menu."""
    # Separator before our items
    context_menu.append(WebKit.ContextMenuItem.new_separator())

    # Reload
    reload_item = WebKit.ContextMenuItem.new_from_stock_action(
        WebKit.ContextMenuAction.RELOAD
    )
    context_menu.append(reload_item)

    # Quit
    app = webview.get_root().get_application()
    quit_action = Gio.SimpleAction.new("quit-gcal", None)
    quit_action.connect("activate", lambda *_: app.quit())
    app.add_action(quit_action)
    quit_item = WebKit.ContextMenuItem.new_from_gaction(
        quit_action, "Quit gcal-desktop", None
    )
    context_menu.append(quit_item)

    return False  # show the menu


def _on_decide_policy(webview, decision, decision_type):
    """Handle navigation policy decisions.

    When a page tries to open a new window (e.g., Google OAuth popup),
    we intercept it and load the URL in the main webview instead.
    This avoids the WebKit WindowFeatures crash on some versions.
    """
    if decision_type == WebKit.PolicyDecisionType.NEW_WINDOW_ACTION:
        nav_action = decision.get_navigation_action()
        request = nav_action.get_request()
        uri = request.get_uri()
        if uri:
            decision.ignore()
            webview.load_uri(uri)
            return True
    decision.use()
    return True


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

        if not self.args.no_layer_shell:
            LayerShell.init_for_window(window)
            LayerShell.set_layer(window, LAYER_MAP[self.args.layer])

            LayerShell.set_anchor(window, LayerShell.Edge.TOP, True)
            LayerShell.set_anchor(window, LayerShell.Edge.BOTTOM, True)
            LayerShell.set_anchor(window, LayerShell.Edge.LEFT, True)
            LayerShell.set_anchor(window, LayerShell.Edge.RIGHT, True)

            LayerShell.set_exclusive_zone(window, -1)

            LayerShell.set_keyboard_mode(
                window, LayerShell.KeyboardMode.ON_DEMAND
            )

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
        else:
            window.set_default_size(1280, 900)

        # --- WebView ---
        webview = WebKit.WebView(network_session=self.network_session)
        configure_webview_settings(webview)

        webview.set_hexpand(True)
        webview.set_vexpand(True)

        webview.connect("decide-policy", _on_decide_policy)
        webview.connect("context-menu", _on_context_menu, None)

        network_session = self.network_session
        webview.connect(
            "load-failed-with-tls-errors",
            lambda wv, uri, cert, errors: _on_tls_error(
                wv, uri, cert, errors, network_session
            ),
        )

        window.set_child(webview)
        window.present()

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
    return app.run(sys.argv[:1])


if __name__ == "__main__":
    raise SystemExit(main())
