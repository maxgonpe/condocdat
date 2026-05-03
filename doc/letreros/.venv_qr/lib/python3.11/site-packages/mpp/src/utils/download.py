import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile

import mpp.src.utils.constants as cst


def shell_exec_as_user():
    """
    Download ShellExecAsUser.dll for NSIS:
    https://nsis.sourceforge.io/mediawiki/images/c/c7/ShellExecAsUser.zip

    Returns:
        str: patht to the downloaded file
    """

    def get_zip_name(url):
        return url.split("/")[-1]

    def get_dll_name(url):
        url, _ = os.path.splitext(url)
        return f"{url}.dll"


    # URL and file names
    zipname = get_zip_name(cst.link_shellexecasuser)
    dllname = get_dll_name(zipname)
    dl_output = os.path.dirname(cst.path_dll_shellexecasuser)

    # Temporary download directory
    dir_temp = tempfile.gettempdir()
    dir_path = os.path.join(dir_temp, "tmp_shellexecasuser")
    dl_path = os.path.join(dir_path, zipname)

    # Get ShellExecAsUser.zip file
    if os.path.exists(dl_path):
        print(f"Using cached file from {dl_path}")
    else:
        os.mkdir(dir_path)
        __download(cst.link_shellexecasuser, dl_path)

    # Extract ShellExecAsUSer.dll
    with zipfile.ZipFile(dl_path) as zf:
        zf.extract(dllname, dl_output)

    return cst.path_dll_shellexecasuser


def __download(url_src, path_dst):
    """
    Download a file from an url to a file

    Args:
        url_src (str): url of the file
        path_dst (str): path to the output file
    """

    try:
        print("Downloading...", end=" ")
        with urllib.request.urlopen(url_src) as response:
            with open(path_dst, "wb") as output:
                shutil.copyfileobj(response, output)
        print("Done")
    except urllib.error.URLError:
        sys.exit("No internet connection.")
