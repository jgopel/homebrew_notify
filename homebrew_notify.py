#!/usr/bin/env python3
"""Send OSX notification when a tap or cask update is available in Homebrew"""


def notify(*, text, title=None, subtitle=None):
    """Send an OSX notification"""
    import os
    import json

    command = f"display notification {json.dumps(text)}"
    if title:
        command += f" with title {json.dumps(title)}"
    if subtitle:
        command += f" subtitle {json.dumps(subtitle)}"
    os.system(f"osascript -e '{command}'")
