import json
import os
import sys

from mpp.src.utils import ask, constants as cst


def read():
    """
    Returns the project's configuration parameters.

    Returns:
        dict: project parameters
    """

    try:
        with open(".mpp_config") as f:
            return json.load(f)
    except FileNotFoundError:
        sys.exit("Please setup your environment with `mpp setup`.")


def write(mpp_config:dict):
    """
    Writes the project's configuration file.

    Args:
        mpp_config (dict): project parameters
    """

    # Write the config file
    with open(".mpp_config", "w") as f:
        json.dump(mpp_config, f, indent=4)


def setup(from_=dict(), write_file=True):
    """
    Setup a new mpp_config or from a previous version.

    Args:
        from_ (dict): project parameters
        write_file (bool): create file if true

    Returns:
        dict: updated project parameters
    """

    with open(cst.path_questions) as f:
        questions = json.load(f)
    new_mpp_config = dict()

    try:
        new_mpp_config["name"] = from_["name"]
    except:
        current_dir = os.path.basename(os.getcwd())
        new_mpp_config["name"] = ask.question(questions["name"], current_dir, required=True)

    try:
        new_mpp_config["author"] = from_["author"]
    except:
        username = os.path.basename(os.path.expanduser("~"))
        new_mpp_config["author"] = ask.question(questions["author"], username, required=True)

    try:
        new_mpp_config["version"] = from_["version"]
    except:
        new_mpp_config["version"] = "0.0.0"

    try:
        new_mpp_config["icon"] = from_["icon"]
    except:
        new_mpp_config["icon"] = "resources/images/icon.ico"

    try:
        new_mpp_config["resources"] = from_["resources"]
    except:
        new_mpp_config["resources"] = ["resources", ".mpp_config"]

    try:
        new_mpp_config["console"] = from_["console"]
    except:
        new_mpp_config["console"] = True

    try:
        new_mpp_config["hidden-imports"] = from_["hidden-imports"]
    except:
        new_mpp_config["hidden-imports"] = list()

    if write_file:
        write(new_mpp_config)

    return new_mpp_config
