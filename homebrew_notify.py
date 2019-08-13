#!/usr/bin/env python3
"""Send OSX notification when a tap or cask update is available in Homebrew"""

import collections
import json
import re
import subprocess

from pathlib import Path

INSTALL_DIR = Path.home() / ".homebrew_notify"
SCRIPT_INSTALL_LOCATION = INSTALL_DIR / "homebrew_notify.py"
REPORTED_TAPS_FILE = INSTALL_DIR / "reported_taps.json"
REPORTED_CASKS_FILE = INSTALL_DIR / "reported_casks.json"

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


def store_formula_list(*, formula_list, file_path):
    """Store outdated formulas to a file"""
    with open(file_path, mode="w+") as json_file:
        json.dump([formula._asdict() for formula in formula_list], json_file, indent=4)


def load_formula_list(file_path):
    """Load outdated formulas from a file"""
    try:
        with open(file_path, mode="r") as json_file:
            return [OutdatedFormuala(**tap) for tap in json.load(json_file)]
    except FileNotFoundError:
        return {}


def update_reported_taps(taps):
    """Store reported taps to file"""
    store_formula_list(formula_list=taps, file_path=REPORTED_TAPS_FILE)


def update_reported_casks(casks):
    """Store reported casks to file"""
    store_formula_list(formula_list=casks, file_path=REPORTED_CASKS_FILE)


def get_reporeted_taps():
    """Load reported taps from file"""
    return load_formula_list(REPORTED_TAPS_FILE)


def get_reporeted_casks():
    """Load reported casks from file"""
    return load_formula_list(REPORTED_CASKS_FILE)


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

    outdated_taps = brew_outdated()
    outdated_casks = brew_cask_outdated()

    reported_taps = get_reporeted_taps()
    reported_casks = get_reporeted_casks()

    if outdated_taps != reported_taps or outdated_casks != reported_casks:
        notify_taps_and_casks(taps=outdated_taps, casks=outdated_casks)
        update_reported_taps(outdated_taps)
        update_reported_casks(outdated_casks)


def install():
    """Copy script to home directory and install it in the crontab"""
    def copy_file():
        import shutil
        SCRIPT_INSTALL_LOCATION.parent.mkdir(parents=True, exist_ok=True)
        # TODO: Warn on an update once there's logging
        shutil.copy(src=__file__, dst=SCRIPT_INSTALL_LOCATION)

    def setup_crontab():
        current_crontab = subprocess.run(["crontab", "-l"], check=True, capture_output=True, text=True).stdout.strip()
        if str(SCRIPT_INSTALL_LOCATION) in current_crontab:
            raise RuntimeError("Homebrew Notify already installed in crontab. Not updating crontab.")
        crontab_line = f"*/30 * * * * PATH=/usr/local/bin:$PATH {SCRIPT_INSTALL_LOCATION}"
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
