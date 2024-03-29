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
    parser.add_argument(
        "--uninstall",
        help="Stop automatically notifying and remove installed scripts",
        action="store_true",
    )
    parser.add_argument(
        "--notify-once",
        help="Once a specific update has been notified on (in this mode), prevent further notifications",
        action="store_true",
    )

    args = parser.parse_args()
    return args.install, args.uninstall, args.notify_once


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


def notify_taps_and_casks(*, taps, casks, always_notify):
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
        if always_notify:
            notify(text="", title="No tap or cask updates available")
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


def notify_outdated_formula(*, always_notify=True):
    """Send notification about formula that are outdated"""
    brew_update()

    outdated_taps = brew_outdated()
    outdated_casks = brew_cask_outdated()

    need_to_notify = always_notify
    if not always_notify:
        reported_taps = get_reporeted_taps()
        reported_casks = get_reporeted_casks()
        need_to_notify = outdated_taps != reported_taps or outdated_casks != reported_casks

    if need_to_notify:
        notify_taps_and_casks(taps=outdated_taps, casks=outdated_casks, always_notify=always_notify)
        if not always_notify:
            update_reported_taps(outdated_taps)
            update_reported_casks(outdated_casks)


def get_current_crontab():
    """Get list of current crontab lines"""
    return subprocess.run(["crontab", "-l"], check=True, capture_output=True, text=True).stdout.splitlines()


def remove_pattern_from_crontab(*, crontab, pattern):
    """Remove lines from crontab based on pattern matching"""
    new_crontab = [line for line in crontab if pattern not in line]
    return len(crontab) != len(new_crontab), new_crontab


def remove_self_from_crontab(crontab):
    """Remove homebrew_notify (this script) from crontab"""
    return remove_pattern_from_crontab(crontab=crontab, pattern=str(SCRIPT_INSTALL_LOCATION))


def remove_homebrew_notifier_from_crontab(crontab):
    """Remove homebrew-notifier (the Ruby script) from crontab"""
    return remove_pattern_from_crontab(crontab=crontab, pattern=".homebrew-notifier/notifier.sh")


def update_crontab(new_crontab):
    """Replace crontab with new crontab"""
    subprocess.run(["crontab", "-"], check=True, capture_output=True, text=True, input="\n".join(new_crontab))


def install():
    """Copy script to home directory and install it in the crontab"""
    def copy_file():
        import shutil
        INSTALL_DIR.mkdir(parents=True, exist_ok=True)
        # TODO: Warn on an update once there's logging
        shutil.copy(src=__file__, dst=SCRIPT_INSTALL_LOCATION)

    def setup_crontab():
        # Remove any entries that would duplicate functionality
        crontab = get_current_crontab()
        removed_self, crontab = remove_self_from_crontab(crontab)
        if removed_self:
            print("Replacing currently installed Homebrew Notify")
        removed_ruby, crontab = remove_homebrew_notifier_from_crontab(crontab)
        if removed_ruby:
            print("Removing currently installed Homebrew Notifier (Ruby)")

        # Add self to crontab
        new_line = f"*/30 * * * * PATH=/usr/local/bin:$PATH {SCRIPT_INSTALL_LOCATION} --notify-once"
        crontab.append(new_line)
        update_crontab(crontab)

    copy_file()
    setup_crontab()


def uninstall():
    """Remove all traces of the installed script"""
    def remove_install_directory():
        import shutil
        shutil.rmtree(path=INSTALL_DIR)

    _, crontab = remove_self_from_crontab(get_current_crontab())
    update_crontab(crontab)
    remove_install_directory()


def main():
    """Run when script is run"""

    do_install, do_uninstall, notify_once = parse_args()
    if do_install:
        install()
    elif do_uninstall:
        uninstall()
    else:
        notify_outdated_formula(always_notify=not notify_once)


if __name__ == "__main__":
    main()
