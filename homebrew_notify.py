#!/usr/bin/env python3
"""Send OSX notification when a tap or cask update is available in Homebrew"""

import collections
import json
import re
import subprocess

# Type for casks and taps that are outdated
OutdatedFormuala = collections.namedtuple(typename="OutdatedFormual",
                                          field_names="package installed_version current_version")

# Regex for detecting cask versions
CASK_VERSION_REGEX = re.compile(r"(?P<package>.+) \((?P<installed_version>.+)\) != (?P<current_version>.+)")


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


def brew_cask_outdated():
    """Do the `brew cask outdated` command"""
    outdated_casks = subprocess.check_output(["brew", "cask", "outdated", "--verbose"],
                                             stderr=subprocess.STDOUT).decode("utf8")
    output = []
    for line in outdated_casks.splitlines():
        match = CASK_VERSION_REGEX.match(line)
        if not match:
            continue
        output.append(
            OutdatedFormuala(
                package=match.group("package"),
                installed_version=match.group("installed_version"),
                current_version=match.group("current_version"),
            ))
    return output
