#!/usr/bin/env python3
"""Send OSX notification when a tap or cask update is available in Homebrew"""

import collections
import json
import subprocess

# Type for casks and taps that are outdated
OutdatedFormuala = collections.namedtuple(typename="OutdatedFormual",
                                          field_names="package installed_version current_version")


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


def brew_outdated():
    """Do the `brew outdated` command"""
    outdated_taps = json.loads(subprocess.check_output(["brew", "outdated", "--json=v1"]))
    return [
        OutdatedFormuala(
            package=tap["name"],
            installed_version=tap["installed_versions"][-1],
            current_version=tap["current_version"],
        ) for tap in outdated_taps if not tap["pinned"]
    ]
