# gcal-desktop

Google Calendar rendered as your desktop wallpaper on KDE Plasma 6 (Wayland).

<!-- Screenshot goes here -->

---

## Features

- Renders Google Calendar directly on your desktop background using an embedded WebKit browser
- Sits behind all windows on the desktop layer -- always visible, never in the way
- Survives workspace switches and stays anchored to the correct monitor
- Starts automatically at login via systemd user service or freedesktop autostart entry
- Configurable calendar URL, Wayland layer, and target monitor via CLI flags
- Distributable as a `.deb` package for easy sharing
- No Electron, no extra runtime -- just GTK4 + WebKitGTK + gtk4-layer-shell

---

## Requirements

- **OS:** Kubuntu 24.04 or later (or any distro shipping KDE Plasma 6)
- **Session:** Wayland (X11 is not supported; gtk4-layer-shell requires the `wlr-layer-shell` Wayland protocol)
- **Python:** Python 3.10+

### APT dependencies

```
sudo apt install \
    python3-gi \
    gir1.2-gtk-4.0 \
    gir1.2-webkit-6.0 \
    gir1.2-gtk4layershell-1.0 \
    libgtk4-layer-shell0
```

> **Note:** On distributions that do not yet ship `gir1.2-webkit-6.0`, try
> `gir1.2-webkit2-4.1` as a fallback. Full feature parity is not guaranteed
> with the older WebKit binding.

---

## Installation

### Option A: Install from .deb package

If someone has shared a `.deb` file with you:

```bash
sudo apt install ./gcal-desktop_1.0.0_all.deb
```

This installs the binary, desktop entry, and systemd service file system-wide. After installation, enable the service:

```bash
systemctl --user enable --now gcal-desktop.service
```

### Option B: Install from PKGBUILD (Arch Linux)

```bash
git clone https://github.com/99oblivius/gcal-desktop.git
cd gcal-desktop
makepkg -si
systemctl --user enable --now gcal-desktop.service
```

### Option C: Install from source

#### 1. Install dependencies

```bash
sudo apt install \
    python3-gi \
    gir1.2-gtk-4.0 \
    gir1.2-webkit-6.0 \
    gir1.2-gtk4layershell-1.0 \
    libgtk4-layer-shell0
```

#### 2. Clone the repository

```bash
git clone https://github.com/99oblivius/gcal-desktop.git
cd gcal-desktop
```

#### 3. Run the installer

```bash
bash install.sh
```

The installer will:
- Copy `gcal_desktop.py` to `/usr/local/bin/gcal-desktop` (with executable permissions)
- Install the systemd user service to `~/.config/systemd/user/`
- Ask you to choose between systemd service or XDG autostart

#### Manual installation (alternative)

```bash
sudo install -m 755 gcal_desktop.py /usr/local/bin/gcal-desktop
mkdir -p ~/.config/systemd/user
cp gcal-desktop.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now gcal-desktop.service
```

---

## Building the .deb package

To build a distributable `.deb` package from the source tree:

```bash
bash build-deb.sh
```

This creates `gcal-desktop_1.0.0_all.deb` in the project root. The package includes:

- `/usr/bin/gcal-desktop` -- the main executable
- `/usr/share/applications/gcal-desktop.desktop` -- desktop entry
- `/usr/lib/systemd/user/gcal-desktop.service` -- systemd user service

Requirements for building: `dpkg-deb` (available on any Debian/Ubuntu system).

---

## Running: systemd service vs. autostart

gcal-desktop supports two methods for starting automatically at login.

### systemd user service (recommended)

The systemd approach provides automatic restart on failure, centralized logging, and clean start/stop control.

```bash
# Enable and start
systemctl --user enable --now gcal-desktop.service

# Or via the built-in CLI flag
gcal-desktop --service-install
```

### XDG autostart (.desktop entry)

The traditional method. Your desktop environment launches the app at login. No automatic restart if it crashes.

```bash
mkdir -p ~/.config/autostart
cp gcal-desktop.desktop ~/.config/autostart/
```

### Controlling the systemd service

```bash
# Check status
systemctl --user status gcal-desktop

# Restart
systemctl --user restart gcal-desktop

# Stop
systemctl --user stop gcal-desktop

# View logs (follow mode)
journalctl --user -u gcal-desktop -f

# View recent logs
journalctl --user -u gcal-desktop --since "1 hour ago"
```

### Custom environment variables

If you need to set environment variables for the service (for example, to disable GPU compositing), create the file `~/.config/gcal-desktop/env`:

```bash
mkdir -p ~/.config/gcal-desktop
echo "WEBKIT_DISABLE_COMPOSITING_MODE=1" >> ~/.config/gcal-desktop/env
systemctl --user restart gcal-desktop
```

---

## Usage

```
gcal-desktop [--url URL] [--layer LAYER] [--monitor N]
             [--no-layer-shell]
             [--service-install] [--service-uninstall]
```

| Argument | Default | Description |
|---|---|---|
| `--url URL` | Google Calendar web app URL | Full URL to load in the embedded browser |
| `--layer LAYER` | `bottom` | Wayland layer (`background`, `bottom`, `top`, `overlay`) |
| `--monitor N` | primary | Zero-based index of the monitor to display on |
| `--no-layer-shell` | | Run as a regular window instead of a desktop layer |
| `--service-install` | | Install and enable the systemd user service, then exit |
| `--service-uninstall` | | Disable and remove the systemd user service, then exit |

### Examples

```bash
# Start with defaults (Google Calendar on primary monitor)
gcal-desktop

# Use a specific Google Calendar URL
gcal-desktop --url "https://calendar.google.com/calendar/r/week"

# Place on a second monitor, on the bottom layer
gcal-desktop --monitor 1 --layer bottom

# Install the systemd service from the command line
gcal-desktop --service-install

# Remove the systemd service
gcal-desktop --service-uninstall
```

---

## Uninstalling

### If installed from .deb

```bash
sudo apt remove gcal-desktop
```

The package's pre-removal script automatically stops the service and removes the autostart entry.

### If installed from source

```bash
bash install.sh --uninstall
```

This will:
- Stop and disable the systemd user service (if active)
- Remove the service file from `~/.config/systemd/user/`
- Remove the autostart desktop entry (if present)
- Remove `/usr/local/bin/gcal-desktop`

User data in `~/.local/share/gcal-desktop` and `~/.cache/gcal-desktop` is preserved. Delete those directories manually for a complete cleanup.

---

## How it works

`gcal-desktop` uses two libraries to achieve the wallpaper effect:

1. **gtk4-layer-shell** -- implements the `wlr-layer-shell` Wayland protocol,
   which lets a GTK4 window be placed on a named compositor layer (such as
   `background`) rather than in the normal window stack. KDE KWin on Wayland
   supports this protocol, so the window sits behind every other surface.

2. **WebKitGTK** -- an embeddable web engine (the same engine used by GNOME
   Web / Epiphany) wrapped in a GTK4 widget. It loads Google Calendar's full
   web application, giving you a complete, interactive calendar view including
   sign-in, event creation, and all calendar views.

At startup the script creates a fullscreen GTK4 window, attaches it to the
configured Wayland layer and monitor via gtk4-layer-shell, embeds a WebKit web
view, and navigates to the calendar URL. The result is an always-visible,
click-through-capable calendar that lives at the wallpaper level.

---

## Known limitations

- **Wayland only.** The `wlr-layer-shell` protocol does not exist on X11.
  There is no plan to support X11.
- **KDE Plasma / wlroots-based compositors only.** GNOME's Mutter compositor
  deliberately does not implement `wlr-layer-shell`, so this tool will not
  work on a stock GNOME session.
- **Google re-login.** Google may occasionally prompt for re-authentication.
  Because the WebKit view is a real browser with persistent storage, logging in
  once is usually sufficient, but Google's session policies may force
  periodic re-login.
- **Google Calendar interaction.** Some WebKitGTK versions have a bug where
  Google Calendar's pointer events stop working after the page finishes loading.
  Ensure GStreamer plugins are installed (`gst-plugins-base`, `gst-plugins-good`
  on Arch; `gstreamer1.0-plugins-base`, `gstreamer1.0-plugins-good` on Ubuntu).
- **Hardware acceleration.** WebKit GPU acceleration depends on your graphics
  driver and Mesa version. If you experience rendering glitches, try setting
  the environment variable `WEBKIT_DISABLE_COMPOSITING_MODE=1`.

---

## License

MIT -- see [LICENSE](LICENSE) for the full text.

---

## Contributing

Contributions are welcome. Please open an issue to discuss significant changes
before submitting a pull request. Make sure your code passes any existing tests
and follows the style of the surrounding code.

1. Fork the repository
2. Create a feature branch: `git checkout -b my-feature`
3. Commit your changes: `git commit -m "Add my feature"`
4. Push the branch: `git push origin my-feature`
5. Open a pull request
