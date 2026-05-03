import json
import os
import sys

from mpp.src.utils import constants as cst


def write_spec(mpp_config):
    """
    Writes the PyInstaller spec file and the NSIS file

    Args:
        mpp_config (dict): project parameters
    """

    os.makedirs("installer", exist_ok=True)

    # Write the specs file
    with open(f"installer/installer.spec", "w") as f:
        f.write(cst.pattern_spec % mpp_config)


def write_nsis(mpp_config):
    """
    Writes the NSIS installer file

    Args:
        mpp_config (dict): project parameters
    """

    os.makedirs("installer", exist_ok=True)

    # Write the nsis file
    with open(f"installer/installer.nsi", "w") as f:
        f.write(cst.pattern_nsis % mpp_config)


def write_mpp_config(mpp_config):
    """
    Writes the project's configuration file

    Args:
        mpp_config (dict): project parameters
    """

    # Write the config file
    with open(".mpp_config", "w") as f:
        json.dump(mpp_config, f, indent=4)


def get_mpp_config():
    """
    Returns the project's configuration file

    Returns:
        dict: project parameters
    """

    try:
        with open(".mpp_config") as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit("Please setup your environment with `mpp setup`.")
