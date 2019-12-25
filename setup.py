import sys
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))


# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="vscode_dl",
    version="0.0.1",
    description="Visual Studio Code and extensions downloader for offline installations",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://rene-d.github.io/vscode-dl/",
    author="Rene Devichi",
    author_email="rene.github@gmail.com",
    classifiers=[
        "License :: Public Domain",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Topic :: System :: Archiving :: Mirroring",
        "Topic :: System :: Installation/Setup",
        "Development Status :: 5 - Production/Stable",
        "Operating System :: OS Independent",
    ],
    keywords="vscode visualstudiocode",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.6, <4",
    package_data={"vscode_dl": ["extensions.yaml", "get.py", "index.html"]},
    install_requires=["python-dateutil", "PyYAML", "requests", "requests_cache"],
    entry_points={"console_scripts": ["vscode-dl=vscode_dl.__init__:main"]},
    project_urls={
        "Source": "https://github.com/rene-d/vscode-dl",
        "Bug Reports": "https://github.com/rene-d/vscode-dl/issues",
    },
)
