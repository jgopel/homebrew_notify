#!/usr/bin/env python3
"""Send OSX notification when a tap or cask update is available in Homebrew"""

import collections
import json
import re
import subprocess

from pathlib import Path

INSTALL_DIR = ".homebrew_notify"

# Type for casks and taps that are outdated
OutdatedFormuala = collections.namedtuple(typename="OutdatedFormual",
                                          field_names="package installed_version current_version")

# Regex for detecting cask versions
CASK_VERSION_REGEX = re.compile(r"(?P<package>.+) \((?P<installed_version>.+)\) != (?P<current_version>.+)")


def parse_args():
    """Parse arguments"""
    import argparse

    parser = argparse.ArgumentParser(description="Sends OSX terminal notification if brew has updates available")
    parser.add_argument(
        "--install",
        help="Setup notifier to run automatically",
        action="store_true",
    )

    args = parser.parse_args()
    return args.install


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
    subprocess.run(["brew", "update"], check=True, capture_output=True)


def brew_outdated():
    """Do the `brew outdated` command"""
    outdated_taps = json.loads(
        subprocess.run(["brew", "outdated", "--json=v1"], check=True, capture_output=True, text=True).stdout)
    return [
        OutdatedFormuala(
            package=tap["name"],
            installed_version=tap["installed_versions"][-1],
            current_version=tap["current_version"],
        ) for tap in outdated_taps if not tap["pinned"]
    ]


def brew_cask_outdated():
    """Do the `brew cask outdated` command"""
    outdated_casks = subprocess.run(["brew", "cask", "outdated", "--verbose"],
                                    check=True,
                                    capture_output=True,
                                    text=True).stdout

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


def notify_taps_and_casks(*, taps, casks):
    """Send notification about the provided taps and casks"""
    def get_notification_string(num_items, item_name):
        if num_items < 1:
            return None

        output = f"{num_items} {item_name}"
        if num_items > 1:
            output += "s"
        return output

    # Don't notify if there are no updates
    if not taps + casks:
        return

    # Build notification
    tap_text = get_notification_string(len(taps), "tap")
    cask_text = get_notification_string(len(casks), "cask")
    formulae_text = " and ".join([x for x in [tap_text, cask_text] if x is not None])
    notify(
        title="Homebrew Updates Available",
        subtitle=f"There are updates to {formulae_text}",
        text=" ".join(sorted([x.package for x in taps + casks])),
    )


def notify_outdated_formula():
    """Send notification about formula that are outdated"""
    brew_update()
    notify_taps_and_casks(taps=brew_outdated(), casks=brew_cask_outdated())


def install():
    """Copy script to home directory and install it in the crontab"""
    script_install_location = Path.home() / INSTALL_DIR / "homebrew_notify.py"

    def copy_file():
        import shutil
        script_install_location.parent.mkdir(parents=True, exist_ok=True)
        # TODO: Warn on an update once there's logging
        shutil.copy(src=__file__, dst=script_install_location)

    def setup_crontab():
        current_crontab = subprocess.run(["crontab", "-l"], check=True, capture_output=True, text=True).stdout.strip()
        if str(script_install_location) in current_crontab:
            raise RuntimeError("Homebrew Notify already installed in crontab. Not updating crontab.")
        crontab_line = f"*/30 * * * * PATH=/usr/local/bin:$PATH {script_install_location}"
        new_crontab = "\n".join([current_crontab, crontab_line])
        subprocess.run(["crontab", "-"], check=True, capture_output=True, text=True, input=new_crontab)

    copy_file()
    setup_crontab()


def main():
    """Run when script is run"""

    do_install = parse_args()
    if do_install:
        install()
    else:
        notify_outdated_formula()


if __name__ == "__main__":
    main()
