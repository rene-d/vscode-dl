# dl-vscode

## Description

This Python3 script downloads the latest Linux version of [Visual Studio Code](http://code.visualstudio.com) and some extensions for installation on computers without Internet connection.

The program also creates a catalog in Markdown that can be incorporated into a web page, like `index.html`.

When it is run again, it updates the extensions and VSCode.

## Usage

Download Visual Studio Code and extensions listed in `extensions.yaml` :
````
./dl-vscode.py
````

Scan installed extensions and add them to the download list :
````
./dl-vscode.py -i
````

Download assets for `index.hrml` (showdown, .css and images) :
````
./dl-vscode.py --assets
````

## Links

* [Official site](https://code.visualstudio.com/)
* [Official GitHub](https://github.com/microsoft/vscode)
* [Extensions](https://marketplace.visualstudio.com/vscode)
* [Awesome list for Visual Studio Code](https://github.com/viatsko/awesome-vscode)
