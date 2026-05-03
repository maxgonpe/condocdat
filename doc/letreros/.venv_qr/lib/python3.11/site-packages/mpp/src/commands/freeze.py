import json
import json
import os
import shutil
import sys

from mpp.src.utils import ask, config_file, files


def freeze(args=None):
    """
    Freezes the project to create an executable.

    Args:
        args (argparse args): parameters from parser.parse_args()
    """

    # Get project config file
    mpp_config = config_file.read()

    # Process --spec parameter
    if hasattr(args, "spec") and args.spec is True:
        # Write spec file
        files.write_spec(mpp_config)
        print("PyInstaller spec file can be found here: installer/installer.spec.")
        sys.exit()

    # PyInstaller exists
    if not shutil.which("pyinstaller"):
        print("It seems that PyInstaller is not installed.")
        print("Please, consider using `pip install PyInstaller`.")
        print(f"Current pip is {shutil.which('pip')}.")
        answer = ask.question("Do you want to install it now (y/n)?", "y")
        print("")
        if answer == "y":
            print("~$ pip install PyInstaller")
            os.system("pip install PyInstaller")
            print("")
        else:
            sys.exit()

    # Write spec file
    print("Generate PyInstaller spec file.")
    files.write_spec(mpp_config)
    print("")

    # Execute PyInstaller
    print("~$ pyinstaller installer.spec")
    os.chdir("installer")
    os.system("pyinstaller installer.spec")
    os.chdir("..")
    print("")
    print(f"Executable can be found here: target/{mpp_config['name']}/{mpp_config['name']}.exe")
