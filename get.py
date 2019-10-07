#! /usr/bin/env python3
# rene-d 2018

"""
install or updates Visual Studio Code and its extensions
"""

import argparse
import json
import os
import platform
import subprocess
import tempfile
import shutil
import requests
import urllib
import pathlib


check_mark = "\033[32m\N{heavy check mark}\033[0m"  # ✔
heavy_ballot_x = "\033[31m\N{heavy ballot x}\033[0m"  # ✘
hot_beverage = "\033[1;33m\N{hot beverage}\033[0m"  # ♨

COLOR_RED = "\033[0;31m"
COLOR_GREEN = "\033[0;32m"
COLOR_LIGHT_CYAN = "\033[1;36m"
COLOR_END = "\033[0m"


# keep a reference to the temporaries files
last_temporary_file = []


def download_vsix(url, name):
    """
    download a remote file to a temporary one
    return the filename
    """

    try:
        scheme, netloc, path, _, _ = urllib.parse.urlsplit(url, scheme="file")
        if scheme == "file":
            return pathlib.Path(path) / name

        if path.endswith("/"):
            path += name
        else:
            path += "/" + name
        uri = urllib.parse.urlunsplit((scheme, netloc, path, None, None))

        r = requests.get(uri, stream=True, allow_redirects=True)
        if r.status_code == 200:
            fp = tempfile.NamedTemporaryFile(suffix=("_" + os.path.basename(name)))
            shutil.copyfileobj(r.raw, fp.file)
            fp.file.close()
            last_temporary_file.append(fp)  # noqa
            return pathlib.Path(fp.name)
        else:
            r.raise_for_status()

    except requests.HTTPError as e:
        print("cannot download {}: {}{}{}".format(name, COLOR_RED, e, COLOR_END))


def load_resource(url, name):
    """
    retrieve a local or remote JSON resource
    """

    try:
        scheme, netloc, path, _, _ = urllib.parse.urlsplit(url, scheme="file")
        if scheme == "file":
            with (pathlib.Path(path) / name).open("r") as f:
                return json.load(f)

        if path.endswith("/"):
            path += name
        else:
            path += "/" + name
        uri = urllib.parse.urlunsplit((scheme, netloc, path, None, None))

        r = requests.get(uri)
        if r.status_code == 200:
            data = r.json()
        else:
            r.raise_for_status()

    except Exception as e:
        print("cannot get resource {}: {}{}{}".format(name, COLOR_RED, e, COLOR_END))
        return

    return data


def update_code(url, dry_run, platform):
    """
    install or update Visual Studio Code
    """

    print("installing or updating Visual Studio Code...")

    # load database
    data = load_resource(url, "data.json")
    if not data:
        return
    code = data["code"]

    colorized_key = COLOR_LIGHT_CYAN + "Visual Studio Code" + COLOR_END

    try:
        cmd = subprocess.run(
            ["dpkg-query", "--show", "code"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        if cmd.returncode != 0 and cmd.returncode != 1:
            raise OSError(cmd.returncode)

        version = cmd.stdout.decode()
        if version != "":
            version = version.split()[1]

    except Exception as e:
        print("not running Linux Debian/Ubuntu?")
        print("...don't know how to check Code version neither to install it.")
        print(e)
        return

    if version != code["tag"]:

        if version == "":
            print(
                "installing: {} version {} ({}) {}".format(
                    colorized_key,
                    COLOR_GREEN + code["version"] + COLOR_END,
                    COLOR_GREEN + code["tag"] + COLOR_END,
                    hot_beverage,
                )
            )
        else:
            print(
                "updating: {} from version {} to version {} ({}) {}".format(
                    colorized_key,
                    COLOR_RED + version + COLOR_END,
                    COLOR_GREEN + code["version"] + COLOR_END,
                    COLOR_GREEN + code["tag"] + COLOR_END,
                    hot_beverage,
                )
            )
        if not dry_run:
            deb = download_vsix(url, code["url"])
            if deb:
                subprocess.call(["sudo", "dpkg", "-i", deb])
                subprocess.call(
                    "sudo sed -i 's/^deb/# deb/' /etc/apt/sources.list.d/vscode.list",
                    shell=True,
                    stderr=subprocess.DEVNULL
                )

    else:
        print(
            "{} up to date: {} ({}) {}".format(
                colorized_key,
                COLOR_GREEN + code["version"] + COLOR_END,
                COLOR_GREEN + code["tag"] + COLOR_END,
                check_mark,
            )
        )


def install_extension(url, vsix, dry_run):
    """
    install an extension
    """

    if dry_run:
        cmd = "code --install-extension '{}'".format(pathlib.Path(vsix).name)
        print(COLOR_GREEN + cmd + COLOR_END)
    else:
        vsix_path = download_vsix(url, vsix)
        if vsix_path:
            cmd = "code --install-extension '{}'".format(vsix_path)
            s = subprocess.check_output(cmd, shell=True)
            print("\033[2m" + s.decode() + "\033[0m")


def update_extensions(url, dry_run, platform):
    """
    update installed extensions
    """

    processed = []

    # load database
    data = load_resource(url, "data.json")
    if not data:
        return processed
    extensions = data["extensions"]

    # get installed extensions
    print("fetching installed extensions...")
    s = subprocess.check_output("code --list-extensions --show-versions", shell=True)
    installed = sorted(set(s.decode().split()))

    # do update
    for i in installed:
        try:
            key, version = i.split("@", 1)

            if key == "ms-vscode.cpptools" and platform is not None:
                key = "ms-vscode.cpptools-" + platform

            processed.append(key)

            colorized_key = COLOR_LIGHT_CYAN + key + COLOR_END

            if key not in extensions:
                print(
                    "extension not found: {} {}".format(colorized_key, heavy_ballot_x)
                )

            elif extensions[key]["version"] == version:
                print(
                    "extension up to date: {} ({}) {}".format(
                        colorized_key, version, check_mark
                    )
                )

            else:
                vsix = extensions[key]["vsix"]
                print(
                    "updating: {} from version {} to version {} {}".format(
                        colorized_key, version, extensions[key]["version"], hot_beverage
                    )
                )
                install_extension(url, vsix, dry_run)

        except Exception as e:
            print("error for {}: {}{}{}".format(i, COLOR_RED, e, COLOR_END))

    return processed


def install_extensions(url, dry_run, platform, processed, team):
    """
    """

    # load database
    data = load_resource(url, "data.json")
    if not data:
        return

    data = data["extensions"]
    extensions = load_resource(url, team + ".json")
    if not extensions:
        return

    for key in set(extensions) - set(processed):
        if key not in data:
            if key + "-" + platform in data:
                key = key + "-" + platform
            else:
                print("error", key, platform)
                continue
        vsix = data[key]["vsix"]
        version = data[key]["version"]
        colorized_key = COLOR_LIGHT_CYAN + key + COLOR_END
        print(
            "installing: {} version {} {}".format(colorized_key, version, hot_beverage)
        )
        install_extension(url, vsix, dry_run)


def main():
    """ main function """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", help="increase verbosity", action="store_true"
    )
    parser.add_argument(
        "-n", "--dry-run", help="scan installed extensions", action="store_true"
    )
    parser.add_argument(
        "-E", "--extensions", help="update extensions", action="store_true"
    )
    parser.add_argument(
        "-C", "--code", help="install/update VSCode", action="store_true"
    )
    parser.add_argument(
        "-F", "--favorites", help="install favorite extensions", action="store_true"
    )
    parser.add_argument(
        "-p",
        "--platform",
        help="override platform detection",
        choices=["linux", "win32", "osx", "linux32"],
    )
    parser.add_argument("-t", "--team", help="name of extension list")
    parser.add_argument("url", help="mirror url", nargs="?", default=".")

    args = parser.parse_args()

    if args.platform is None:
        if args.verbose:
            print(platform.uname())
        if platform.system() == "Darwin":
            args.platform = "osx"
        elif platform.system() == "Windows":
            args.platform = "win32"
        elif platform.system() == "Linux":
            if platform.uname().machine in ["i686", "i386"]:
                args.platform = "linux32"
            elif platform.uname().machine in ["amd64", "x86_64"]:
                args.platform = "linux"
    if args.platform is None:
        parser.error("Could not detect a supported platform")

    if args.verbose:
        print(args)

    # by default, process all actions
    if not (args.code or args.extensions or args.favorites):
        args.code = args.extensions = args.favorites = True

    if args.code:
        update_code(args.url, args.dry_run, args.platform)
    if args.extensions:
        processed = update_extensions(args.url, args.dry_run, args.platform)
    else:
        processed = []
    if args.favorites or args.team:
        install_extensions(
            args.url, args.dry_run, args.platform, processed, args.team or "team"
        )


if __name__ == "__main__":
    from platform import system as platform_system

    if platform_system() == "Windows":
        import ctypes

        kernel32 = ctypes.windll.kernel32

        # https://docs.microsoft.com/en-us/windows/console/setconsolemode
        STD_OUTPUT_HANDLE = -11
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

        mode = ctypes.wintypes.DWORD()
        if kernel32.GetConsoleMode(
            kernel32.GetStdHandle(STD_OUTPUT_HANDLE), ctypes.byref(mode)
        ):
            mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            kernel32.SetConsoleMode(kernel32.GetStdHandle(STD_OUTPUT_HANDLE), mode)

    main()
