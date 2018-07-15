# dl-vscode

## Description

This Python3 script downloads the latest Linux version of [Visual Studio Code](http://code.visualstudio.com) and some extensions for installation on computers without Internet connection or proxy restrictions.

The program also creates a catalog in Markdown that can be incorporated into a web page, like `index.html`.

When it is run again, it tries to update extensions and VSCode to their lastest version.

## Requirements

* [Python3](https://www.python.org/downloads/) 3.6 or 3.7 (older ones *won't* work)
* [Requests](http://docs.python-requests.org/en/master/)
* [PyYAML](https://pyyaml.org)

````
pip3 install -U requests PyYAML
````

## Usage

Download Visual Studio Code and extensions listed in `extensions.yaml` :
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

## Links

* [Official site](https://code.visualstudio.com/)
* [Official GitHub](https://github.com/microsoft/vscode)
* [Extensions](https://marketplace.visualstudio.com/vscode)
* [Awesome list for Visual Studio Code](https://github.com/viatsko/awesome-vscode)
* [markdown-it](https://github.com/markdown-it/markdown-it)
* [highlight.js](https://github.com/isagalaev/highlight.js)

## License

[Unlicense](http://unlicense.org) aka. Public Domain ;-)
