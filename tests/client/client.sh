#! /bin/bash

python3 <(curl -skL http://mirror/get.py) http://mirror/

code-tool -V
code-tool -l
code-tool -i ms-vscode.Go
code-tool -i ms-python.python

code --version
code --list-extensions --show-versions
