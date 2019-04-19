#! /usr/bin/env python3
# rene-d 2018

import argparse
import json
import os
import platform
import subprocess
import tempfile

import requests

check_mark = "\033[32m\N{heavy check mark}\033[0m"  # ✔
heavy_ballot_x = "\033[31m\N{heavy ballot x}\033[0m"  # ✘
hot_beverage = "\033[1;33m\N{hot beverage}\033[0m"  # ♨

COLOR_RED = "\033[0;31m"
COLOR_GREEN = "\033[0;32m"
COLOR_LIGHT_CYAN = "\033[1;36m"
COLOR_END = "\033[0m"

temporary_files = []


def download_vsix(url, vsix):
    r = requests.get(url + "/" + vsix)
    if r.status_code == 200:
        fp = tempfile.NamedTemporaryFile(suffix="_" + os.path.basename(vsix))
        fp.file.write(r.content)
        fp.file.close()
        temporary_files.append(fp)
        return fp.name
    else:
        r.raise_for_status()


def update_extensions(url, dry_run=False, platform=None):

    # load database
    try:
        if url is None:
            with open("code.json", "r") as f:
                extensions = json.load(f)["extensions"]
        else:
            r = requests.get(url + "/code.json")
            if r.status_code == 200:
                extensions = r.json()["extensions"]
            else:
                r.raise_for_status()
    except Exception as e:
        print("cannot get extensions data: {}{}{}".format(COLOR_RED, e, COLOR_END))
        return

    # get installed extensions
    s = subprocess.check_output("code --list-extensions --show-versions", shell=True)
    installed = sorted(set(s.decode().split()))

    # do update
    for i in installed:
        try:
            key, version = i.split("@", 1)

            if key == "ms-vscode.cpptools" and platform is not None:
                key = "ms-vscode.cpptools-" + platform

            colorized_key = COLOR_LIGHT_CYAN + key + COLOR_END

            if key not in extensions:
                print("extension not found: {} {}".format(colorized_key, heavy_ballot_x))

            elif extensions[key]["version"] == version:
                print("extension up to date: {} ({}) {}".format(colorized_key, version, check_mark))

            else:
                vsix = extensions[key]["vsix"]

                if not dry_run and url:
                    vsix = download_vsix(url, vsix)

                print(
                    "updating: {} from version {} to version {} {}".format(
                        colorized_key, version, extensions[key]["version"], hot_beverage
                    )
                )
                cmd = "code --install-extension '{}'".format(vsix)

                if dry_run:
                    print(COLOR_GREEN + cmd + COLOR_END)
                else:
                    s = subprocess.check_output(cmd, shell=True)
                    print(s.decode())

        except Exception as e:
            print("error for {}: {}{}{}".format(i, COLOR_RED, e, COLOR_END))


def main():
    """ main function """

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase verbosity", action="store_true")
    parser.add_argument("-n", "--dry-run", help="scan installed extensions", action="store_true")
    parser.add_argument("-p", "--platform", help="override platform detection", choices=["linux", "win32", "osx", "linux32"])
    parser.add_argument("url", help="mirror's url", nargs="?")

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

    os.chdir(os.path.dirname(__file__))

    update_extensions(args.url, args.dry_run, args.platform)


if __name__ == "__main__":
    from platform import system as platform_system

    if platform_system() == "Windows":
        import ctypes

        kernel32 = ctypes.windll.kernel32

        # https://docs.microsoft.com/en-us/windows/console/setconsolemode
        STD_OUTPUT_HANDLE = -11
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004

        mode = ctypes.wintypes.DWORD()
        if kernel32.GetConsoleMode(kernel32.GetStdHandle(STD_OUTPUT_HANDLE), ctypes.byref(mode)):
            mode = mode.value | ENABLE_VIRTUAL_TERMINAL_PROCESSING
            kernel32.SetConsoleMode(kernel32.GetStdHandle(STD_OUTPUT_HANDLE), mode)

    main()
