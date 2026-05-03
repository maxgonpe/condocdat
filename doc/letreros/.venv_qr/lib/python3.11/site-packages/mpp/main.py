#!/usr/bin/env python

import argparse
import sys

from mpp.src.commands import setup, config, freeze, installer, version


__version__ = "0.1.9"


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    parser.add_argument("--version", dest="show_version", action="store_true", help="show version and exit")

    setup_parser = subparsers.add_parser(
        "setup",
        description="Ask some questions to setup the project",
        help="ask some questions to setup the project"
    )
    setup_parser.set_defaults(func=setup)

    config_parser = subparsers.add_parser(
        "config",
        description="Show project parameters and edit them",
        help="show project parameters and edit them"
    )
    config_parser.add_argument("parameters", metavar="parameter", nargs="*", help="parameters to edit")
    config_parser.add_argument("--list", action="store_true", help="show project parameters")
    config_parser.add_argument("--update", action="store_true", help="update configuration with the new mpp version")
    config_parser.set_defaults(func=config)

    freeze_parser = subparsers.add_parser(
        "freeze",
        description="Create an executable using PyInstaller",
        help="create an executable using PyInstaller"
    )
    freeze_parser.add_argument("--spec", action="store_true", help="only generate the PyInstaller spec file")
    freeze_parser.set_defaults(func=freeze)

    installer_parser = subparsers.add_parser(
        "installer",
        description="Create an installer with NSIS",
        help="create an installer with NSIS"
    )
    installer_parser.add_argument("--spec", action="store_true", help="only generate the NSIS spec file")
    installer_parser.set_defaults(func=installer)

    version_parser = subparsers.add_parser(
        "version",
        description="Show or increment version number",
        help="Fast increment version number"
    )
    version_parser.set_defaults(func=version)
    version_parser.add_argument("number", nargs="?", help="new or increment version number (+, ++, ...)")

    args = parser.parse_args()

    if args.show_version == True:
        print(f"My Python Project {__version__}")
        sys.exit(0)
    elif not hasattr(args, "func"):
        parser.print_help()
        sys.exit(0)

    args.func(args)
