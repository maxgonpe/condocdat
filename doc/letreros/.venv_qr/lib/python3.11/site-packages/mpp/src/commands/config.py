import json
import os
import shutil
import sys
import textwrap

from mpp.src.utils import ask, config_file, constants as cst


def config(args=None):
    """
    Show or edit configuration parameters

    Args:
        args (argparse args): parameters from parser.parse_args()
    """

    # If there is no parameter
    if not any([args.parameters, args.list, args.update]):
        print("This command needs parameters.")
        print("Use `mpp config --help` to show the help.")
        sys.exit()

    # Get project config file
    mpp_config = config_file.read()

    # If there is list parameter
    if args.list:
        __show_config(mpp_config)
        sys.exit()

    # If there is update parameter
    if args.update:
        # Update project config
        config_file.setup(from_=mpp_config)
        sys.exit("Update done.")

    # If there are parameters
    for param in args.parameters:
        if param not in mpp_config:
            valid = [f"'{x}'" for x in mpp_config.keys()]
            valid = ", ".join(valid)
            sys.exit(f"Invalid parameter: '{param}' (choose from {valid})")

    new_config = __process_parameters(args, mpp_config)
    if new_config:
        mpp_config.update(**new_config)
        config_file.write(mpp_config)


def __show_config(mpp_config):
    """
    Shows the parameters from the configurtion file

    Args:
        mpp_config (dict): project parameters
    """

    values = [f" -→ {k} = {v}" for k, v in mpp_config.items()]
    print(*values, sep="\n")


def __process_parameters(args, mpp_config):
    """
    Processes the given parameters

    Args:
        args (argparse args): parameters from parser.parse_args()
        mpp_config (dict): project parameters

    Returns:
        dict: user's answers
    """

    with open(cst.path_questions) as f:
        questions = json.load(f)

    # Process each parameter
    answers = dict()
    if "name" in args.parameters:
        answers["name"] = ask.question(
            questions["name"],
            default=mpp_config["name"]
        )
    if "author" in args.parameters:
        answers["author"] = ask.question(
            questions["author"],
            default=mpp_config["author"]
        )
    if "version" in args.parameters:
        answers["version"] = ask.question(
            questions["version"],
            default=mpp_config["version"]
        )
    if "resources" in args.parameters:
        answers["resources"] = __process_resources(mpp_config)
    if "console" in args.parameters:
        answers["console"] = ask.question(
            questions["console"],
            default="y" if mpp_config["console"] else "n"
        )
        answers["console"] = answers["console"].lower() == "y"
    if "hidden-imports" in args.parameters:
        answers["hidden-imports"] = __process_hidden_imports(mpp_config)

    # Validate modifications
    print("")
    is_ok = ask.question(
        questions["confirm"],
        required=True
    ).lower() == "y"

    if not is_ok:
        answers.clear()

    return answers


def __process_resources(mpp_config):
    """
    Processes the `resources` parameter

    Args:
        mpp_config (dict): project parameters

    Returns:
        list: user's resources
    """

    resources = mpp_config["resources"][:]
    help_msg = textwrap.dedent("""\
    Use `-<file>` to remove a file or `+<file>` to add it.
    Use `list` to display the current resources.
    Use `clear` to remove all the resources.
    Use `help` to show this message.
    Use `q` to exit.""")

    print("List of current resources:")
    print(f"[{', '.join(resources)}]")
    print("")
    print(help_msg)

    while True:
        answer = input("> ")

        # Verify input
        if len(answer.split()) > 1:
            print("White spaces are not allowed.")
            continue

        # Exit
        if answer == "q":
            break
        # Show help
        elif answer == "help":
            print(help_msg)
        # Remove all
        elif answer == "clear":
            resources.clear()
        # Display list of resources
        elif answer == "list":
            print(f"[{', '.join(resources)}]")
        # Remove one package
        elif answer.startswith("-"):
            try:
                resources.remove(answer[1:])
            except ValueError:
                print(f"`{answer[1:]}` is not part of the resources.")
        # Add one package
        elif answer.startswith("+"):
            resources.append(answer[1:])
        # Something else
        else:
            print(f"`{answer}` is not a valid entry.")

    return sorted(set(resources))


def __process_hidden_imports(mpp_config):
    """
    Processes the `hidden-imports` parameter

    Args:
        mpp_config (dict): project parameters

    Returns:
        list: user's hidden-imports
    """

    imports = mpp_config["hidden-imports"][:]
    help_msg = textwrap.dedent("""\
    Use `-<package>` to remove a package or `+<package>` to add it.
    Use `list` to display the current imports.
    Use `clear` to remove all the packages.
    Use `help` to show this message.
    Use `q` to exit.""")

    print("List of current hidden imports:")
    print(f"[{', '.join(imports)}]")
    print("")
    print(help_msg)

    while True:
        answer = input("> ")

        # Verify input
        if len(answer.split()) > 1:
            print("White spaces are not allowed.")
            continue

        # Exit
        if answer == "q":
            break
        # Show help
        elif answer == "help":
            print(help_msg)
        # Remove all
        elif answer == "clear":
            imports.clear()
        # Display list of imports
        elif answer == "list":
            print(f"[{', '.join(imports)}]")
        # Remove one package
        elif answer.startswith("-"):
            try:
                imports.remove(answer[1:])
            except ValueError:
                print(f"`{answer[1:]}` is not part of the hidden imports.")
        # Add one package
        elif answer.startswith("+"):
            imports.append(answer[1:])
        # Something else
        else:
            print(f"`{answer}` is not a valid entry.")

    return sorted(set(imports))
