# VSCode Downloader

## Description

[vscode-dl](https://rene-d.github.io/vscode-dl) is a Python3 script that downloads the latest Linux version of [Visual Studio Code](http://code.visualstudio.com) and a curated list of extensions for installation on computers without Internet connection or proxy restrictions.

The program also creates a catalog in JSON and Markdown that can be incorporated into a web page, like this [example](https://rene-d.github.io/vscode-dl/demo.html).

When run again, it tries to update extensions and VSCode to their latest version.

## Requirements

* [Python3](https://www.python.org/downloads) : version 3.6 or 3.7 (older ones *won't* work because of [f-strings](https://www.python.org/dev/peps/pep-0498))
* [Requests](http://python-requests.org) and [Requests-cache](https://github.com/reclosedev/requests-cache)
* [PyYAML](https://pyyaml.org)

```bash
pip3 install -U -r requirements.txt
```

## Basic usage

Download Visual Studio Code and extensions listed in `extensions.yaml` ([screenshot](http://rene-d.github.io/vscode-dl/screenshot.html)) :
```bash
python3 vscode-dl.py
```

Scan installed extensions and add them to the download list :
```bash
python3 vscode-dl.py -i
```

More options are available. Use `python3 vscode-dl.py --help` to show them.

## Installation and update tool

On a offline installation, [get.py](get.py) install or updates Code, downloads and updates the installed extensions from the mirror.

It requires Python 3.5+ and [requests](http://python-requests.org) that should be installed on all modern Debian/Ubuntu.

```bash
# One-liner:
curl -sL http://mirror.url:port/get.py | python3 - http://mirror.url:port/

# Alternatively, you can run the script into the mirror folder:
cd /path/to/vscode-mirror
python3 get.py
```

The flag `-t` permits to provide a minimal set of extensions to be installed. They should be listed in a JSON array.

Example of a file `myteam.json` (to be copied in the mirror directory):
```JSON
["ms-python.python", "formulahendry.code-runner"]
```

The following command wil install or update Code and the extensions listed above.
```bash
python3 <(curl -sL http://mirror.url:port/get.py) -t myteam http://mirror.url:port/
```

## Links

* [Official Visual Studio Code site](https://code.visualstudio.com/)
* [Official GitHub](https://github.com/microsoft/vscode)
* [Extensions](https://marketplace.visualstudio.com/vscode)
* [Awesome list for Visual Studio Code](https://github.com/viatsko/awesome-vscode)
* [markdown-it](https://github.com/markdown-it/markdown-it)
* [highlight.js](https://github.com/isagalaev/highlight.js)

## License

[Unlicense](http://unlicense.org) aka. Public Domain 😀
