import json
import os
import shutil
import sys

from mpp.src.utils import ask, config_file, constants as cst


def setup(args=None):
    """
    Asks information to the user and setup the environment

    Args:
        args (argparse args): parameters from parser.parse_args()
    """

    # Ask questions
    mpp_config = config_file.setup()

    # Create folders
    os.makedirs("resources/images", exist_ok=True)
    os.makedirs("src", exist_ok=True)

    # Add icon
    if not os.path.exists(mpp_config["icon"]):
        shutil.copy(cst.path_ico_default, mpp_config["icon"])
    # Write main file
    if not os.path.exists("main.py"):
        with open("main.py", "w") as f:
            f.write(cst.pattern_main_py % mpp_config)

    print("")
    print(f"The project's version is {mpp_config['version']}.")
    print(f"The project's icon can be found here: {mpp_config['icon']}.")
    print("The `main.py` file can now be edited.")
    print("")
    print("Use `mpp --help` to display all possible commands.")
    print("Use `mpp <command> -h` to display the help for a command.")
    print("Use `mpp config --list` to show your project's settings.")
