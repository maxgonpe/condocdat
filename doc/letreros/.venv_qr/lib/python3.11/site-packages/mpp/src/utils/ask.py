
def question(message, default="", required=False):
    """
    Ask a question to the user

    Args:
        message (str): message to display
        default (str): the default value
        required (bool): if True, loop to get an answer

    Returns:
        str: user's value
    """

    # Do while
    while True:
        # Adapt the message to add the default answer
        if default != "":
            message += f" [{default}] "
        elif not message.endswith(" "):
            message += " "

        # Ask the question
        answer = input(message)
        if answer == "":
            answer = default

        # Verify if it should be asked again
        if answer != "":
            break
        else:
            if required is False:
                break

    return answer
