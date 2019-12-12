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

## Run with Docker

A Dockerfile is provided to run the app into a container, with interpreter and requirements ready-to-use.

```bash
# build the image
docker build -t vscode_dl .

# run the downloader
docker run -ti --rm -v /path/to/mirror:/app/web vscode_dl

# run the downloader with an alternate extension list
docker run -ti --rm -v /path/to/mirror:/app/web -v /path/to/extensions.yaml:/app/extensions.yaml vscode_dl
```

## Installation and update tool

### First use

On a offline installation, [get.py](get.py) install or updates Code, downloads and updates the installed extensions from the mirror.

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

### The tool : `code-tool`

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

As the time of writing (December 2019), only x64, armhf (32-bit) and Alpine/amd64 platforms are available. arm64 will come soon.

## The Go extension case

The [Go extension](https://marketplace.visualstudio.com/items/ms-vscode.Go) requires some Go packages to be functional (linter, formatter, code analyzer, etc.). These dependencies are listed into the extension, that tries to install them from Internet. To bypass this step, the sync program (`vscode-dl.py`- uses `go get -d` commands to download the required packages, and the update tool (`get.py` aka. `code-tool`) installs them in `~/go` (default GOPATH). Thus, the GOPATH environment variable should include at least this directory.

## Links

* [Official Visual Studio Code site](https://code.visualstudio.com/)
* [Official GitHub](https://github.com/microsoft/vscode)
* [Extensions](https://marketplace.visualstudio.com/vscode)
* [Awesome list for Visual Studio Code](https://github.com/viatsko/awesome-vscode)
* [markdown-it](https://github.com/markdown-it/markdown-it)
* [highlight.js](https://github.com/isagalaev/highlight.js)

## License

[Unlicense](http://unlicense.org) aka. Public Domain 😀
