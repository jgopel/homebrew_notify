#!/usr/bin/env python3
"""Send OSX notification when a tap or cask update is available in Homebrew"""

import json
import subprocess


def notify(*, text, title=None, subtitle=None):
    """Send an OSX notification"""
    import os

    command = f"display notification {json.dumps(text)}"
    if title:
        command += f" with title {json.dumps(title)}"
    if subtitle:
        command += f" subtitle {json.dumps(subtitle)}"
    os.system(f"osascript -e '{command}'")


def brew_update():
    """Do the `brew update` command"""
    subprocess.check_call(["brew", "update"], stdout=subprocess.DEVNULL)
