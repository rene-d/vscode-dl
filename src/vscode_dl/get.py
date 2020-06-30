#! /usr/bin/env python3
# rene-d 2019

"""
install or updates Visual Studio Code and its extensions
"""

import sys
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
import re
import logging
import textwrap

################################

DEFAULT_URL = "."  # modified when tool is installed locally
LOCAL_MODE = False  # True when tool is installed locally
TOOL_VERSION = 35  # numerical value, strictly incremental

################################

if sys.stdout.encoding != "UTF-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf8", buffering=1)
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf8", buffering=1)

CHECK_MARK = "\033[32m\N{heavy check mark}\033[0m"  # ✔
HEAVY_BALLOT_X = "\033[31m\N{heavy ballot x}\033[0m"  # ✘
HOT_BEVERAGE = "\033[1;33m\N{hot beverage}\033[0m"  # ♨

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
            return pathlib.Path(fp.name).as_posix()
        else:
            r.raise_for_status()

    except requests.HTTPError as e:
        print("cannot download {}: {}{}{}".format(name, COLOR_RED, e, COLOR_END))


def load_resource(url, name, raw=False):
    """
    retrieve a local or remote JSON resource
    """

    try:
        scheme, netloc, path, _, _ = urllib.parse.urlsplit(url, scheme="file")
        if scheme == "file":
            with (pathlib.Path(path) / name).open("rb") as f:
                if raw:
                    return f.read()
                else:
                    return json.load(f)

        if path.endswith("/"):
            path += name
        else:
            path += "/" + name
        uri = urllib.parse.urlunsplit((scheme, netloc, path, None, None))

        r = requests.get(uri)
        if r.status_code == 200:
            if raw:
                data = r.content
            else:
                data = r.json()
        else:
            r.raise_for_status()

    except Exception as e:
        print("cannot get resource {}: {}{}{}".format(name, COLOR_RED, e, COLOR_END))
        return

    return data


def update_code(url, dry_run, platform, data):
    """
    install or update Visual Studio Code
    """

    print("\033[95mInstalling or updating Visual Studio Code...\033[0m")

    # get code database
    code = data["code"]

    colorized_key = COLOR_LIGHT_CYAN + "Visual Studio Code" + COLOR_END

    try:
        cmd = subprocess.run(["dpkg-query", "--show", "code"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        if cmd.returncode != 0 and cmd.returncode != 1:
            raise OSError(cmd.returncode)

        version = cmd.stdout.decode()
        if version != "":
            version = version.split()[1]

    except Exception as e:
        print("not running Linux Debian/Ubuntu?")
        print("...don't know how to check Code version neither to install it.")
        print("\033[2m" + repr(e) + "\033[0m")
        return

    if version != code["tag"]:

        if version == "":
            print(
                "installing: {} version {} ({}) {}".format(
                    colorized_key,
                    COLOR_GREEN + code["version"] + COLOR_END,
                    COLOR_GREEN + code["tag"] + COLOR_END,
                    HOT_BEVERAGE,
                )
            )
        else:
            print(
                "updating: {} from version {} to version {} ({}) {}".format(
                    colorized_key,
                    COLOR_RED + version + COLOR_END,
                    COLOR_GREEN + code["version"] + COLOR_END,
                    COLOR_GREEN + code["tag"] + COLOR_END,
                    HOT_BEVERAGE,
                )
            )
        if not dry_run:
            deb = download_vsix(url, code["url"])
            if deb:
                # call dpkg to install the .deb
                cmd = ["dpkg", "-i", deb]
                if os.getuid() != 0:
                    cmd.insert(0, "sudo")
                subprocess.call(cmd)

                # deactivate the source list
                cmd = ["sed", "-i", "s/^deb/# deb/", "/etc/apt/sources.list.d/vscode.list"]
                if os.getuid() != 0:
                    cmd.insert(0, "sudo")
                subprocess.call(cmd, stderr=subprocess.DEVNULL)

            settings = pathlib.Path("~/.config/Code/User/settings.json").expanduser()
            if settings.exists() is False or settings.stat().st_size == 0:
                settings.parent.mkdir(parents=True, exist_ok=True)
                with settings.open("w") as fd:
                    fd.write(
                        """\
{
    "update.mode": "none",
    "update.showReleaseNotes": false,
    "extensions.autoCheckUpdates": false,
    "extensions.autoUpdate": false,
    "telemetry.enableCrashReporter": false,
    "telemetry.enableTelemetry": false,
    "files.trimTrailingWhitespace": true,
    "files.trimFinalNewlines": true,
}"""
                    )
                print("created: {}".format(settings))

    else:
        print(
            "{} up to date: {} ({}) {}".format(
                colorized_key,
                COLOR_GREEN + code["version"] + COLOR_END,
                COLOR_GREEN + code["tag"] + COLOR_END,
                CHECK_MARK,
            )
        )


def print_cmd(cmd):
    """
    print a command line
    """
    s = " ".join(a if a.find(" ") == -1 else '"' + a + '"' for a in cmd)
    print("\033[2mexec: {}\033[0m".format(s))


def update_go_tools(url, dry_run, tools):
    """
    mirror and build Go tools
    """
    print("\033[95mSyncing Go tools...\033[0m")

    if not url.startswith("http") and not url.startswith("ftp"):
        url = "file://" + url

    # get the archive and untar it
    cmd = "curl -skL {}/go-tools.tar.gz | tar -xzf -".format(url)
    if not dry_run:
        subprocess.call(cmd, shell=True, cwd="/usr/local")
    else:
        print_cmd(cmd)

    env = os.environ.copy()
    #env["GOPATH"] = pathlib.Path("~/go").expanduser().as_posix()

    for tool in tools.values():
        cmd = ["go", "get", tool["importPath"]]
        if not dry_run:
            print("installing: \033[1;36m{}\033[0m".format(tool["name"]))
            subprocess.call(cmd, env=env)
        else:
            print_cmd(cmd)


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
            try:
                s = subprocess.check_output(cmd, shell=True)
                print("\033[2m" + s.decode() + "\033[0m")
            except subprocess.CalledProcessError as e:
                print("error:", e)


def update_extensions(url, dry_run, platform, data):
    """
    update installed extensions
    """

    processed = set()

    if os.getuid() == 0:
        print("error: cannot update extensions as root")
        return processed

    # get extension database
    extensions = data["extensions"]

    # add keys in lowercase
    for key in list(extensions.keys()):
        if key != key.lower():
            extensions[key.lower()] = extensions[key]

    # get installed extensions
    print("\033[95mFetching installed extensions...\033[0m")
    s = subprocess.check_output("code --list-extensions --show-versions", shell=True)
    installed = sorted(set(s.decode().split()))

    defer = []

    # do update
    for i in installed:
        try:
            key, version = i.split("@", 1)

            if key == "ms-vscode.cpptools" and platform is not None:
                key = "ms-vscode.cpptools-" + platform

            processed.add(key)

            colorized_key = COLOR_LIGHT_CYAN + key + COLOR_END

            extension = extensions.get(key.lower())

            if extension is None:
                print("extension not found: {} {}".format(colorized_key, HEAVY_BALLOT_X))
                continue

            if extension["version"] == version:
                print("extension up to date: {} ({}) {}".format(colorized_key, version, CHECK_MARK))

            else:
                vsix = extension["vsix"]
                print(
                    "updating: {} from version {} to version {} {}".format(
                        colorized_key, version, extension["version"], HOT_BEVERAGE
                    )
                )
                install_extension(url, vsix, dry_run)

            if key == "golang.Go":
                defer.append(lambda: update_go_tools(url, dry_run, data["go-tools"]))

        except Exception as e:
            logging.error("error for {}: {}{}{}".format(i, COLOR_RED, e, COLOR_END))

    for action in defer:
        action()

    return processed


def install_extensions(url, dry_run, platform, extensions_list, data):
    """
    """

    if os.getuid() == 0:
        print("error: cannot install extensions as root")
        return

    extensions = data["extensions"]

    defer = []

    for key in extensions_list:
        if key not in extensions:
            if key + "-" + platform in extensions:
                key = key + "-" + platform
            else:
                print("error: extension not found {}".format(key))
                continue
        vsix = extensions[key]["vsix"]
        version = extensions[key]["version"]
        colorized_key = COLOR_LIGHT_CYAN + key + COLOR_END
        print("installing: {} version {} {}".format(colorized_key, version, HOT_BEVERAGE))
        install_extension(url, vsix, dry_run)

        if key == "golang.Go":
            defer.append(lambda: update_go_tools(url, dry_run, data["go-tools"]))

    for action in defer:
        action()


def update_tool(url, data):
    """ update local tool """

    print("\033[95mInstalling or updating companion tool...\033[0m")
    logging.debug("url %s", url)
    logging.debug("DEFAULT_URL %s", DEFAULT_URL)
    logging.debug("LOCAL_MODE %s", LOCAL_MODE)

    # get the remote version and source code
    remote_code = load_resource(url, "get.py", raw=True)
    if remote_code is None:
        return

    remote_code = remote_code.replace(b'\nDEFAULT_URL = "."', b'\nDEFAULT_URL = "%s"' % (url.encode()), 1)
    remote_code = remote_code.replace(b"\nLOCAL_MODE = False", b"\nLOCAL_MODE = True", 1)

    remote_version = re.search(rb"TOOL_VERSION = (\d+)", remote_code)
    if remote_version is None:
        logging.warning("Remote script too old. Cannot update.")
        return
    remote_version = int(remote_version.group(1))

    local_path = pathlib.Path("~/.local/bin/code-tool").expanduser()

    if LOCAL_MODE:
        if remote_version == TOOL_VERSION:
            # local tool is up to date
            # print("local tool is already in version {}".format(remote_version))
            return
        else:
            action = "updated"
    else:
        # install the tool in ~/.local/bin
        if local_path.exists():
            local_code = local_path.open("rb").read()
            local_version = int(re.search(rb"TOOL_VERSION = (\d+)", local_code).group(1))
            if local_version == TOOL_VERSION:
                logging.debug("local tool is already in version {}".format(remote_version))
                return
            action = "updated"
        else:
            action = "installed"

    local_path.parent.mkdir(parents=True, exist_ok=True)
    with local_path.open("wb") as f:
        f.write(remote_code)
    local_path.chmod(0o755)
    print("code-tool has been {} into ~/.local/bin".format(action))
    print("You may add this directory to your PATH and `rehash` (zsh users)")

    if LOCAL_MODE:
        print("Please re-run code-tool")
        exit()


def list_extensions(url, data, verbose):
    """ list available extensions """

    try:
        cols = int(subprocess.check_output(["tput", "cols"]))
    except Exception:
        cols = 100

    print("List of available extensions")
    print()

    if cols < 200:
        color = ["\033[94m", "\033[33m"]
        for extension in sorted(data["extensions"].keys()):
            description = data["extensions"][extension]["description"]
            print("    \033[92m" + extension + "\033[0m")
            for c2 in textwrap.wrap(
                description, initial_indent="        ", subsequent_indent="        ", width=cols - 10
            ):
                print(c2)

    elif False:
        w1 = max(len(extension) for extension in data["extensions"].keys())
        w2 = max(len(v["version"]) for v in data["extensions"].values())
        fmt = ("{:%d} | {:>%d} | " % (w1, w2)).format
        n = 0
        color = ["\033[97m", "\033[94m"]
        for extension, desc in data["extensions"].items():
            n += 1
            c1 = fmt(extension, desc["version"])
            for c2 in textwrap.wrap(desc["description"], width=cols - w1 - w2 - 8):
                print(color[n % 2] + c1 + c2 + "\033[0m")
                c1 = fmt("", "")
    else:
        w1 = max(len(extension) for extension in data["extensions"].keys())
        fmt = ("{:%d} | " % (w1)).format

        print(fmt("Tag") + "Description")
        print(fmt("-" * w1) + "-" * 50)
        n = 0
        color = ["\033[97m", "\033[94m"]
        for extension in sorted(data["extensions"].keys()):
            description = data["extensions"][extension]["description"]
            n += 1
            c1 = fmt(extension)
            for c2 in textwrap.wrap(description, width=cols - w1 - 4):
                print(color[n % 2] + c1 + c2 + "\033[0m")
                c1 = fmt("")


def main():
    """ main function """

    # logger options
    if sys.stdout.isatty():
        logging.addLevelName(logging.DEBUG, "\033[0;32m%s\033[0m" % logging.getLevelName(logging.DEBUG))
        logging.addLevelName(logging.INFO, "\033[1;33m%s\033[0m" % logging.getLevelName(logging.INFO))
        logging.addLevelName(logging.WARNING, "\033[1;35m%s\033[0m" % logging.getLevelName(logging.WARNING))
        logging.addLevelName(logging.ERROR, "\033[1;41m%s\033[0m" % logging.getLevelName(logging.ERROR))

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase verbosity", action="store_true")
    parser.add_argument("-V", "--version", help="show version and url", action="store_true")
    parser.add_argument("-n", "--dry-run", help="scan installed extensions", action="store_true")
    parser.add_argument(
        "-p", "--platform", help="override platform detection", choices=["linux", "win32", "osx", "linux32"]
    )
    parser.add_argument("-u", "--update", help="do updates", action="store_true")
    parser.add_argument("-C", "--code", help="install/update VSCode", action="store_true")
    parser.add_argument("-E", "--extensions", help="update extensions", action="store_true")
    parser.add_argument("-F", "--favorites", help="install favorite extensions", action="store_true")
    parser.add_argument("-t", "--team", help="name of extension list")
    parser.add_argument("-i", "--install-extension", help="install extension", action="append")
    parser.add_argument("-l", "--list-extensions", help="list available extensions", action="store_true")
    parser.add_argument("url", help="mirror url", nargs="?", default=DEFAULT_URL)
    parser.add_argument("--mirror-url", action="store_true", help=argparse.SUPPRESS, dest="mirror_url")

    args = parser.parse_args()

    # hidden option to get the mirror URL
    if args.mirror_url:
        print(DEFAULT_URL)
        exit(0)

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

    if args.url == ".":
        args.url = pathlib.Path(".").absolute().as_posix()

    if args.verbose:
        logging.basicConfig(format="%(asctime)s:%(levelname)s:%(message)s", level=logging.DEBUG, datefmt="%H:%M:%S")
        logging.debug("args {}".format(args))

    if args.version:
        print("Version: {}".format(TOOL_VERSION))
        print("Mode: {}".format(["remote", "remote"][LOCAL_MODE]))
        print("URL: {}".format(DEFAULT_URL))

        data = load_resource(args.url, "data.json")
        if data:
            print()
            print("code: {} {} {}".format(data["code"]["version"], data["code"]["channel"], data["code"]["commit_id"]))
            print("extensions: {}".format(len(data["extensions"])))

        exit()

    data = load_resource(args.url, "data.json")
    if not data:
        logging.error("Cannot retrieve data")
        exit(2)

    # install update tool
    update_tool(args.url, data)

    if args.list_extensions:
        list_extensions(args.url, data, args.verbose)
        exit()

    if args.update:
        args.code = True
        args.extensions = True

    # by default, process all actions
    if not (args.code or args.extensions or args.favorites or args.install_extension):
        if LOCAL_MODE:
            parser.print_help()
            exit()
        args.code = args.extensions = args.favorites = True

    # install/update vscode
    if args.code:
        update_code(args.url, args.dry_run, args.platform, data)

    # update extensions
    if args.extensions:
        processed = update_extensions(args.url, args.dry_run, args.platform, data)
    else:
        processed = set()

    # install extensions
    if args.favorites or args.team or args.install_extension:

        if args.install_extension:
            extensions = set(args.install_extension)
        else:
            extensions = set()

        if args.favorites or args.team:
            team = load_resource(args.url, (args.team or "team") + ".json")
            if team:
                extensions = extensions.union(set(team))

        extensions = extensions - processed

        install_extensions(args.url, args.dry_run, args.platform, extensions, data)


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
