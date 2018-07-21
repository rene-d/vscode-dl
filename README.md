# dl-vscode

## Description

[dl-vscode](https://rene-d.github.io/dl-vscode) is a Python3 script that downloads the latest Linux version of [Visual Studio Code](http://code.visualstudio.com) and a curated list of extensions for installation on computers without Internet connection or proxy restrictions.

The program also creates a catalog in JSON and Markdown that can be incorporated into a web page, like this [example](https://rene-d.github.io/dl-vscode/demo/).

When run again, it tries to update extensions and VSCode to their latest version.

## Requirements

* [Python3](https://www.python.org/downloads) : version 3.6 or 3.7 (older ones *won't* work because of [f-strings](https://www.python.org/dev/peps/pep-0498))
* [Requests](http://python-requests.org)
* [PyYAML](https://pyyaml.org)

````
pip3 install -U requests PyYAML
````

## Usage

Download Visual Studio Code and extensions listed in `extensions.yaml` ([screenshot](http://rene-d.github.io/dl-vscode/screenshot.md)) :
````
python3 dl-vscode.py
````

Scan installed extensions and add them to the download list :
````
python3 dl-vscode.py -i
````

Download assets for `index.html` (javascript, .css and images) :
````
python3 dl-vscode.py --assets
````

## Extensions update tool

On a offline installation, [update-extensions.py](update-extensions.py) downloads and updates the installed extensions (Python3 and [Requests](http://python-requests.org) package required) from the mirror.

````bash
# One-liner:
curl -s http://mirror.url:port/update-extensions.py | python3 - http://mirror.url:port/

# Alternatively, you can run the script into the mirror folder:
cd /path/to/vscode-mirror
python3 update-extensions.py
````

## Links

* [Official Visual Studio Code site](https://code.visualstudio.com/)
* [Official GitHub](https://github.com/microsoft/vscode)
* [Extensions](https://marketplace.visualstudio.com/vscode)
* [Awesome list for Visual Studio Code](https://github.com/viatsko/awesome-vscode)
* [markdown-it](https://github.com/markdown-it/markdown-it)
* [highlight.js](https://github.com/isagalaev/highlight.js)

## License

[Unlicense](http://unlicense.org) aka. Public Domain 😀
