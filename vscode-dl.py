#!/usr/bin/env python3

"""
To keep compatibility with the old repository
"""

import sys
import subprocess
import importlib
import pathlib

sys.path.append("/tmp/vscode_dl-packages")
cwd = pathlib.Path(__file__).parent.resolve().as_posix()

try:
    # try to import vscode-dl package
    from vscode_dl.vscode_dl import main
except ModuleNotFoundError:
    # install the package from local dir
    subprocess.check_call(
        [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--target", "/tmp/vscode_dl-packages",
            "--upgrade",
            ".",
        ],
        cwd=cwd

    )
    # now we can import it
    importlib.invalidate_caches()
    from vscode_dl.vscode_dl import main

main()
