# gcal-desktop

Google Calendar rendered as your desktop wallpaper on KDE Plasma 6 (Wayland).

<!-- Screenshot goes here -->

---

## Features

- Renders Google Calendar directly on your desktop background using an embedded WebKit browser
- Sits behind all windows on the desktop layer — always visible, never in the way
- Survives workspace switches and stays anchored to the correct monitor
- Starts automatically at login via a freedesktop autostart entry
- Configurable calendar URL, Wayland layer, and target monitor via CLI flags
- No Electron, no extra runtime — just GTK4 + WebKitGTK + gtk4-layer-shell

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

### 1. Install dependencies

```bash
sudo apt install \
    python3-gi \
    gir1.2-gtk-4.0 \
    gir1.2-webkit-6.0 \
    gir1.2-gtk4layershell-1.0 \
    libgtk4-layer-shell0
```

### 2. Clone the repository

```bash
git clone https://github.com/99oblivius/gcal-desktop.git
cd gcal-desktop
```

### 3. Run the installer

```bash
bash install.sh
```

The installer will:
- Copy `gcal_desktop.py` to `/usr/local/bin/gcal-desktop` (with executable permissions)
- Copy `gcal-desktop.desktop` to `~/.config/autostart/` so the app launches automatically at login

### Manual installation (alternative)

```bash
sudo install -m 755 gcal_desktop.py /usr/local/bin/gcal-desktop
mkdir -p ~/.config/autostart
cp gcal-desktop.desktop ~/.config/autostart/
```

---

## Usage

```
gcal-desktop [--url URL] [--layer LAYER] [--monitor N]
```

| Argument | Default | Description |
|---|---|---|
| `--url URL` | Google Calendar web app URL | Full URL to load in the embedded browser |
| `--layer LAYER` | `bottom` | Wayland layer to place the window on (`background`, `bottom`, `top`) |
| `--monitor N` | primary | Zero-based index of the monitor to display on |

### Examples

```bash
# Start with defaults (Google Calendar on primary monitor)
gcal-desktop

# Use a specific Google Calendar URL
gcal-desktop --url "https://calendar.google.com/calendar/r/week"

# Place on a second monitor, on the bottom layer
gcal-desktop --monitor 1 --layer bottom
```

After installation the app is registered as an autostart entry and will launch
automatically with your next Plasma session. To start it immediately without
rebooting:

```bash
gcal-desktop &
```

---

## How it works

`gcal-desktop` uses two libraries to achieve the wallpaper effect:

1. **gtk4-layer-shell** — implements the `wlr-layer-shell` Wayland protocol,
   which lets a GTK4 window be placed on a named compositor layer (such as
   `background`) rather than in the normal window stack. KDE KWin on Wayland
   supports this protocol, so the window sits behind every other surface.

2. **WebKitGTK** — an embeddable web engine (the same engine used by GNOME
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
- **Hardware acceleration.** WebKit GPU acceleration depends on your graphics
  driver and Mesa version. If you experience rendering glitches, try setting
  the environment variable `WEBKIT_DISABLE_COMPOSITING_MODE=1`.

---

## License

MIT — see [LICENSE](LICENSE) for the full text.

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
