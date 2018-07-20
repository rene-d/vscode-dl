# dl-vscode

## Description

This Python3 script downloads the latest Linux version of [Visual Studio Code](http://code.visualstudio.com) and some extensions for installation on computers without Internet connection or proxy restrictions.

The program also creates a catalog in Markdown that can be incorporated into a web page, like this [example](https://rene-d.github.io/dl-vscode/demo/index.html).

When it is run again, it tries to update extensions and VSCode to their latest version.

## Requirements

* [Python3](https://www.python.org/downloads/) 3.6 or 3.7 (older ones *won't* work because of [f-strings](https://www.python.org/dev/peps/pep-0498))
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
