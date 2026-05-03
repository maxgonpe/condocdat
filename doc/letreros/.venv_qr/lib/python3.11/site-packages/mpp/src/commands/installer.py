import json
import os
import shutil
import sys

from mpp.src.commands import freeze
from mpp.src.utils import ask, config_file, download, files, constants as cst


def installer(args=None):
    """
    Creates an installer with the created executable with `freeze`

    Args:
        args (argparse args): parameters from parser.parse_args()
    """

    # Get project config file
    mpp_config = config_file.read()

    # Process --spec parameter
    if hasattr(args, "spec") and args.spec is True:
        # Write spec file
        files.write_nsis(mpp_config)
        print("NSIS spec file can be found here: installer/installer.nsi.")
        sys.exit()

    # Freeze command executed
    if not os.path.isdir(f"target/{mpp_config['name']}"):
        print("It seems that the `freeze` command wasn't executed.")
        answer = ask.question("Do you want to do it now (y/n)?", "y")
        print("")
        if answer == "y":
            freeze()
        else:
            sys.exit()

    # Makensis exists
    if not shutil.which("makensis"):
        print("It seems that NSIS is not installed or set in the PATH.")
        print("It can be found at this address: https://nsis.sourceforge.io/Download")
        sys.exit()

    # ShellExecAsUser exists
    if not os.path.exists(cst.path_dll_shellexecasuser):
        print("NSIS needs \"ShellExecAsUser\" in order to create the installer.")
        answer = ask.question("Do you want to download it (y/n)?", "y")
        print("")
        if answer == "y":
            download.shell_exec_as_user()
            print("")
        else:
            print("It can be found at this address: https://nsis.sourceforge.io/ShellExecAsUser_plug-in")
            sys.exit()

    # Write spec file
    print("Generate NSIS spec file.")
    files.write_nsis(mpp_config)
    print("")

    # Execute the makensis
    print("~$ makensis installer.nsi")
    os.chdir("installer")
    os.system("makensis installer.nsi")
    os.chdir("..")
    print("")
    print(f"Installer can be found here: target/{mpp_config['name']}_setup.exe")
