# Maintainer: gcal-desktop contributors
pkgname=gcal-desktop
pkgver=1.0.0
pkgrel=1
pkgdesc='Google Calendar rendered as your desktop wallpaper on Wayland'
arch=('any')
url='https://github.com/99oblivius/gcal-desktop'
license=('MIT')
depends=(
    'python-gobject'
    'gtk4'
    'webkitgtk-6.0'
    'gtk4-layer-shell'
)
source=("git+https://github.com/99oblivius/gcal-desktop.git")
sha256sums=('SKIP')

package() {
    cd "$srcdir/gcal-desktop"

    # Main executable
    install -Dm755 gcal_desktop.py "$pkgdir/usr/bin/gcal-desktop"

    # Desktop entry
    install -Dm644 gcal-desktop.desktop "$pkgdir/usr/share/applications/gcal-desktop.desktop"

    # systemd user service (with corrected ExecStart path)
    install -Dm644 gcal-desktop.service "$pkgdir/usr/lib/systemd/user/gcal-desktop.service"
    sed -i 's|ExecStart=.*|ExecStart=/usr/bin/gcal-desktop|' \
        "$pkgdir/usr/lib/systemd/user/gcal-desktop.service"

    # License
    install -Dm644 LICENSE "$pkgdir/usr/share/licenses/$pkgname/LICENSE"
}
