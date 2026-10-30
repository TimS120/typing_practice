#!/usr/bin/env python3
"""Register the app identity and icon with the current Linux desktop user."""
import os
from pathlib import Path
import shutil
import subprocess
import sys


def quote_exec(value):
    return '"' + str(value).replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%') + '"'


def main():
    root = Path(__file__).resolve().parent.parent
    python = root / ".venv" / "bin" / "python"
    if not python.is_file():
        python = Path(sys.executable).resolve()
    data_home = os.environ.get("XDG_DATA_HOME")
    applications = (Path(data_home) if data_home and Path(data_home).is_absolute()
                    else Path.home() / ".local" / "share") / "applications"
    applications.mkdir(parents=True, exist_ok=True)
    entry = applications / "typing-practice.desktop"
    icon = str(root / "assets" / "app_icon_transparent.png").replace('\\', '\\\\').replace('\n', '\\n')
    entry.write_text('\n'.join([
        "[Desktop Entry]", "Type=Application", "Name=Typing Practice",
        "Comment=Typing practice and statistics",
        f"Exec={quote_exec(python)} {quote_exec(root / 'main.py')}",
        f"Icon={icon}", "Terminal=false", "Categories=Education;",
        "StartupWMClass=Typingpractice", "",
    ]), encoding="utf-8")
    if shutil.which("update-desktop-database"):
        subprocess.run(["update-desktop-database", str(applications)], check=True)
    print(f"Installed {entry}")


if __name__ == "__main__":
    main()
