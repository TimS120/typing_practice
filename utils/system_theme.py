"""Read the desktop appearance preference without changing system settings."""
import re
import subprocess
import sys


def _query(arguments: list[str]) -> str:
    try:
        return subprocess.run(arguments, capture_output=True, text=True, timeout=1,
                              check=False).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return ""


def system_prefers_dark() -> bool:
    if sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
        except OSError:
            return False
    if sys.platform == "darwin":
        return _query(["defaults", "read", "-g", "AppleInterfaceStyle"]).lower() == "dark"
    # The portal covers GNOME, KDE and other supporting Linux desktops.
    portal = _query(["gdbus", "call", "--session", "--dest", "org.freedesktop.portal.Desktop",
                     "--object-path", "/org/freedesktop/portal/desktop", "--method",
                     "org.freedesktop.portal.Settings.Read", "org.freedesktop.appearance", "color-scheme"])
    match = re.search(r"uint32\s+([012])", portal)
    if match and match[1] != "0":
        return match[1] == "1"
    preference = _query(["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"])
    if "prefer-dark" in preference:
        return True
    if "prefer-light" in preference:
        return False
    return "dark" in _query(["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"]).lower()
