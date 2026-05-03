import re
import sys

from mpp.src.utils import config_file


def version(args=None):
    """
    Fast increment the version number

    Args:
        args (argparse args): parameters from parser.parse_args()
    """

    # Get project config file
    mpp_config = config_file.read()

    # Show current project version
    if args.number is None:
        print(mpp_config["name"], mpp_config["version"])
        sys.exit()

    # If not an increment, it's a new version number
    if set(args.number) != {"+"}:
        mpp_config["version"] = args.number
        config_file.write(mpp_config)
        sys.exit()

    # If it's not possible to increment
    if not re.match(r"\d+(\.\d+)*", mpp_config["version"]):
        print(f"Version number \"{mpp_config['version']}\" cannot be incremented, the shape X.Y...Z was expected.")
        sys.exit()

    # Increment version number
    ver = [int(v) for v in mpp_config["version"].split(".")]
    index = args.number.count("+")
    if index > len(ver):
        print(f"Too many '+': got {index} but maximum expected is {len(ver)}")
        sys.exit()

    # Increase version number
    ver[-index] += 1
    # Set lower version numbers to 0
    for i in range(-index + 1, 0):
        ver[i] = 0

    # Write config
    ver = ".".join([str(v) for v in ver])
    mpp_config["version"] = ver
    config_file.write(mpp_config)
    print(mpp_config["name"], ver)
