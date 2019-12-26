# VSCode Downloader

[![Build Status](https://travis-ci.org/rene-d/vscode-dl.svg?branch=master)](https://travis-ci.org/rene-d/vscode-dl)
[![pyi](https://img.shields.io/pypi/v/vscode-dl.svg)](https://pypi.python.org/pypi/vscode-dl)
[![pyi](https://img.shields.io/pypi/pyversions/vscode-dl.svg)](https://pypi.python.org/pypi/vscode-dl)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)


## Description

[vscode-dl](https://rene-d.github.io/vscode-dl) is a Python3 script that downloads the latest Linux version of [Visual Studio Code](http://code.visualstudio.com) and a curated list of extensions for installation on computers without Internet connection or proxy restrictions.

The program also creates a catalog in JSON and Markdown that can be incorporated into a web page, like this [example](https://rene-d.github.io/vscode-dl/demo.html).

When run again, it tries to update extensions and VSCode to their latest version.

## Installation

### Requirements

* [Python3](https://www.python.org/downloads) : version >= 3.6 (older ones *won't* work because of [f-strings](https://www.python.org/dev/peps/pep-0498)). The companion tool (see below) requires Python >= 3.5.

### pip

This installs the latest stable, released version.

```bash
pip3 install -U vscode-dl
```

### virtualenv

```bash
python3 -m venv vscode-dl
vscode-dl/bin/pip install vscode-dl
vscode-dl/bin/vscode-dl --help
```

### from GitHub repository

```bash
pip3 install -r requirements.txt

# install the package
python3 setup.py install

# run directly from source
cd src/vscode_dl
./vscode_dl.py --help
```

## Basic usage

Download Visual Studio Code and extensions listed in `extensions.yaml` (if found, otherwise the default list) into the `web/` subdirectory ([screenshot](http://rene-d.github.io/vscode-dl/screenshot.html)) :
```bash
vscode-dl
```

Scan installed extensions and add them to the download list :
```bash
vscode-dl -i
```

More options are available. Use `vscode-dl --help` to show them.

## Run with Docker

A Dockerfile is provided to run the app into a container, with interpreter and requirements ready-to-use.

```bash
# build the image
docker build -t vscode-dl .

# run the downloader
docker run -ti --rm -v /path/to/mirror:/app/web vscode-dl

# run the downloader with an alternate extension list
docker run -ti --rm -v /path/to/mirror:/app/web -v /path/to/extensions.yaml:/app/extensions.yaml vscode-dl
```

## Installation and update tool

### First use

On a offline installation, [get.py](src/vscode_dl/get.py) install or updates Code, downloads and updates the installed extensions from the mirror.

It requires Python 3.5+ and [requests](http://python-requests.org) that should be installed on all modern Debian/Ubuntu.

```bash
curl -skL http://mirror.url:port/get.py | python3 - http://mirror.url:port/
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

### The companion tool : `code-tool`

The tool installs itself into `~/.local/bin/code-tool`. This tool can be used to maintenance tasks and install new extensions. You may have to add this directory to your PATH.

```bash
# update Code and extensions
code-tool -u

# display version and mirror url
code-tool -V

# list available extensions
code-tool -l

# install an extension
code-tool -i <extension.key>
```

More options are available. Use `code-tool --help` to show them.

## The development container

Code allows you to [develop inside a container](https://code.visualstudio.com/docs/remote/containers). Unluckily, this feature requires Internet connection since the remote server is downloaded when attaching to the container, unless this server is already installed. This is the aim of scripts into [container/](container/) subdirectory.

It can be easily adapted to an existing build environment, even for SSH remote development.

As the time of writing (December 2019), only x64, armhf, arm64 and Alpine/amd64 platforms are available.

## The Go extension case

The [Go extension](https://marketplace.visualstudio.com/items/ms-vscode.Go) requires some Go packages to be functional (linter, formatter, code analyzer, etc.). These dependencies are listed into the extension, that tries to install them from Internet. To bypass this step, the sync program (`vscode-dl` uses `go get -d` command to download the required packages, and the update tool (`get.py` aka. `code-tool`) installs them in `~/go` (default GOPATH). Thus, the GOPATH environment variable should include at least this directory.

## Links

* [Official Visual Studio Code site](https://code.visualstudio.com/)
* [Official GitHub](https://github.com/microsoft/vscode)
* [Extensions](https://marketplace.visualstudio.com/vscode)
* [Awesome list for Visual Studio Code](https://github.com/viatsko/awesome-vscode)
* [markdown-it](https://github.com/markdown-it/markdown-it)
* [highlight.js](https://github.com/isagalaev/highlight.js)

## License

[Unlicense](http://unlicense.org) aka. Public Domain 😀
