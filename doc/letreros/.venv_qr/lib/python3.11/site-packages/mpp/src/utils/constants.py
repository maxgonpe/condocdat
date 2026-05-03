import os

pp = os.path.dirname
dir_home = pp(pp(pp(__file__)))

path_questions = os.path.join(dir_home, "resources", "questions.json")
path_ico_default = os.path.join(dir_home, "resources", "default.ico")
path_dll_shellexecasuser = os.path.join("installer", "ShellExecAsUser.dll")
link_shellexecasuser = "https://nsis.sourceforge.io/mediawiki/images/c/c7/ShellExecAsUser.zip"

with open(os.path.join(dir_home, "resources", "main.py.pattern")) as f:
    pattern_main_py = f.read()

with open(os.path.join(dir_home, "resources", "spec.pattern")) as f:
    pattern_spec = f.read()

with open(os.path.join(dir_home, "resources", "nsis.pattern")) as f:
    pattern_nsis = f.read()
