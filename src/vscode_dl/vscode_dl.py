#! /usr/bin/env python3
# rene-d 2018
# modified DaeHyun Sung, 2023.

import argparse
import bz2
import datetime
import email.utils
import json
import logging
import os
import pathlib
import re
import subprocess
import sys
from collections import defaultdict
from operator import itemgetter

import dateutil.parser
import requests
import requests_cache
import yaml
import shutil
import urllib
import zipfile
import pkg_resources

################################

CPPTOOLS_KEY = "ms-vscode.cpptools"
CPPTOOLS_PLATFORMS = ["linux", "win32", "osx", "linux32"]

################################

if sys.stdout.encoding != "UTF-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf8", buffering=1)
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf8", buffering=1)

# logger options
if sys.stdout.isatty():
    logging.addLevelName(
        logging.DEBUG, "\033[0;32m%s\033[0m" % logging.getLevelName(logging.DEBUG)
    )
    logging.addLevelName(
        logging.INFO, "\033[1;33m%s\033[0m" % logging.getLevelName(logging.INFO)
    )
    logging.addLevelName(
        logging.WARNING, "\033[1;35m%s\033[1;0m" % logging.getLevelName(logging.WARNING)
    )
    logging.addLevelName(
        logging.ERROR, "\033[1;41m%s\033[1;0m" % logging.getLevelName(logging.ERROR)
    )

# be a little more visual like npm ;-)
CHECK_MARK = "\033[32m\N{check mark}\033[0m"  # ✔
HEAVY_BALLOT_X = "\033[31m\N{heavy ballot x}\033[0m"  # ✘


def my_parsedate(text):
    """
    parse date from http headers response
    """
    return datetime.datetime(*email.utils.parsedate(text)[:6])


def download(url, file):
    """
    download a file and set last modified time
    """

    if isinstance(file, str):
        file = pathlib.Path(file)

    file.parent.mkdir(exist_ok=True, parents=True)

    with requests_cache.disabled():

        headers = {}
        if os.path.isfile(file):
            headers["If-Modified-Since"] = email.utils.format_datetime(
                datetime.datetime.fromtimestamp(os.stat(file).st_mtime)
            )

        with requests.get(url, stream=True, allow_redirects=True, headers=headers) as r:
            if r.status_code == 200:
                d = os.path.dirname(file)
                if d != "":
                    os.makedirs(d, exist_ok=True)
                with open(file, "wb") as f:
                    for chunk in r.iter_content(chunk_size=4096):
                        f.write(chunk)
                if r.headers.get("last-modified"):
                    d = my_parsedate(r.headers["last-modified"])
                    timestamp = d.timestamp()
                    try:
                        os.utime(file, (timestamp, timestamp))
                    except OSError:
                        pass
                return True

            elif r.status_code == 304:
                # Not Modified
                return True

            else:
                print(HEAVY_BALLOT_X, r.status_code, url)
                return False


# cf. vs/platform/extensionManagement/node/extensionGalleryService.ts
class FilterType:
    #   Tag = 1
    ExtensionId = 4
    #   Category = 5
    ExtensionName = 7
    Target = 8
    #   Featured = 9
    #   SearchText = 10
    ExcludeWithFlags = 12


class Flags:
    #   None = 0x0
    IncludeVersions = 0x1
    IncludeFiles = 0x2
    #   IncludeCategoryAndTags = 0x4
    #   IncludeSharedAccounts = 0x8
    IncludeVersionProperties = 0x10
    #   ExcludeNonValidated = 0x20
    IncludeInstallationTargets = 0x40
    IncludeAssetUri = 0x80
    IncludeStatistics = 0x100
    IncludeLatestVersionOnly = 0x200
    Unpublished = 0x1000


def is_engine_valid(engine, extension):
    """
    check if extension version <= engine version
    Nota: the sematic follows https://semver.org
    """
    extv = ""
    if extension[0] != "^":
        extv = ''.join(i for i in extension if i.isdigit() or i in './\\')
    else:
        extv = ''.join(i for i in extension[1:] if i.isdigit() or i in './\\')
    if engine == "*" or extension == "*":
        return True
    if extension[0] != "^":
        if extension[0].isdigit():
            # sometimes, there's not the leading ^·
            extension = "^" + extension
        else:
            # if version doesn't begin with ^ or a digit, I don't know how to handle it
            logging.error(
                "unknown engine version semantic: %s (current: %s)", extension, engine
            )
            return False
    a = list(map(int, engine.split(".")))
    b = list(map(int, extv.split(".")))
    return a >= b


def get_extensions(extensions, vscode_engine):
    """
    retrieve from server the extension list with engine version validated
    """

    # proceed in two times, like VSCode, to reduce bandwidth consumption
    #    1. get the extension latest versions
    #    2. check if engine is ok
    #    3. make a new query for extensions for which engine doesn't fit

    # prepare the first query
    data = {
        "filters": [
            {
                "criteria": [
                    {
                        "filterType": FilterType.Target,
                        "value": "Microsoft.VisualStudio.Code",
                    },
                    {
                        "filterType": FilterType.ExcludeWithFlags,
                        "value": str(Flags.Unpublished),
                    },
                ]
            }
        ],
        "flags": Flags.IncludeLatestVersionOnly
        + Flags.IncludeAssetUri
        + Flags.IncludeVersionProperties,
    }
    for ext in sorted(extensions):
        data["filters"][0]["criteria"].append(
            {"filterType": FilterType.ExtensionName, "value": ext}
        )

    headers = {
        "Content-type": "application/json",
        "Accept": "application/json;api-version=3.0-preview.1",
    }

    # query the gallery
    logging.debug("query IncludeLatestVersionOnly")
    # json.dump(data, open("query1.json", "w"), indent=2)

    req = requests.post(
        "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery",
        json=data,
        headers=headers,
    )
    res = req.json()

    # json.dump(res, open("response1.json", "w"), indent=2)

    # analyze the response
    not_compatible = []
    result = []

    if "results" in res and "extensions" in res["results"][0]:
        for e in res["results"][0]["extensions"]:

            logging.debug(
                "%s.%s %s",
                e["publisher"]["publisherName"],
                e["extensionName"],
                e["versions"][0]["version"],
            )

            engines = list(
                p["value"]
                for p in e["versions"][0]["properties"]
                if p["key"] == "Microsoft.VisualStudio.Code.Engine"
            )
            for engine in engines:
                if is_engine_valid(vscode_engine, engine):
                    break
            else:
                logging.warning(
                    "engine %r does not match engine %s", engines, vscode_engine
                )
                # we will look for a suitable version later
                not_compatible.append(e["extensionId"])
                continue

            # logging.debug(
            #     "OK: '%s | %s | %s | %s",
            #     e["displayName"],
            #     e.get("shortDescription", e["displayName"]),
            #     e["publisher"]["displayName"],
            #     e["versions"][0]["version"],
            # )
            result.append(e)

    if len(not_compatible) == 0:
        # we have all we need
        return result

    # prepare the second query
    data = {
        "filters": [
            {
                "criteria": [
                    {
                        "filterType": FilterType.Target,
                        "value": "Microsoft.VisualStudio.Code",
                    },
                    {
                        "filterType": FilterType.ExcludeWithFlags,
                        "value": str(Flags.Unpublished),
                    },
                ]
            }
        ],
        "flags": Flags.IncludeVersions
        + Flags.IncludeAssetUri
        + Flags.IncludeVersionProperties,
    }
    for id in not_compatible:
        data["filters"][0]["criteria"].append(
            {"filterType": FilterType.ExtensionId, "value": id}
        )

    # query the gallery
    logging.debug("query IncludeVersions")
    # json.dump(data, open("query2.json", "w"), indent=2)
    req = requests.post(
        "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery",
        json=data,
        headers=headers,
    )
    res = req.json()
    # json.dump(res, open("response2.json", "w"), indent=2)

    if "results" in res and "extensions" in res["results"][0]:
        for e in res["results"][0]["extensions"]:

            logging.debug(
                "analyze %s.%s (%d versions)",
                e["publisher"]["publisherName"],
                e["extensionName"],
                len(e["versions"]),
            )

            # find the greatest version compatible with our vscode engine
            max_vernum = []
            max_version = None
            max_engine = None

            for v in e["versions"]:
                if "properties" not in v:
                    continue

                engine = None
                for p in v["properties"]:
                    if p["key"] == "Microsoft.VisualStudio.Code.Engine":
                        engine = p["value"]
                if engine:
                    is_valid = is_engine_valid(vscode_engine, engine)
                    # logging.debug("found version %s engine %s : %s", v["version"], engine, is_valid)
                    if is_valid:
                        # well, it seems that versions are sorted latest first
                        # but I prefer looking for the greatest version number
                        vernum = list(map(int, v["version"].split(".")))
                        if vernum > max_vernum:
                            max_vernum = vernum
                            max_version = v
                            max_engine = engine

            if max_version:
                logging.debug(
                    "version %s is the best suitable choice, engine %s",
                    max_version["version"],
                    max_engine,
                )
                e["versions"] = [max_version]
            else:
                logging.error("no suitable version found")

            result.append(e)

    return result


def parse_date(d):
    """
    return a suitable date for markdown
    """
    return dateutil.parser.parse(d).strftime("%Y/%m/%d&nbsp;%H:%M:%S")


def process_cpptools(dst_dir, json_data, e):
    """
    download the online installer for C/C++ extension
    """

    key = CPPTOOLS_KEY
    version = e["versions"][0]["version"]

    platforms = ["linux"]

    # fetch all releases
    releases = requests.get(
        "https://api.github.com/repos/Microsoft/vscode-cpptools/releases"
    )

    if releases.status_code != 200:
        return

    # request is successfull
    for release in releases.json():
        # find the version matching one
        if release["name"] != version:
            continue

        for asset in release["assets"]:
            if asset["content_type"] != "application/vsix":
                continue
            if asset["state"] != "uploaded":
                continue

            platform = re.search(r"^cpptools-(.+)\.vsix$", asset["name"])
            if platform is None:
                continue

            platform = platform.group(1)
            if platform not in platforms:
                continue

            key2 = key + "-" + platform

            vsix = "vsix/" + key2 + "-" + version + ".vsix"

            json_data["extensions"][key2] = {
                "version": version,
                "vsix": vsix,
                "vsixAsset": asset["browser_download_url"],
                "name": e["displayName"] + " (" + platform + ")",
                "url": "https://marketplace.visualstudio.com/items?itemName=" + key,
                "icon": "icons/" + (key + ".png"),
                "iconAsset": f'{e["versions"][0]["assetUri"]}/Microsoft.VisualStudio.Services.Icons.Small',
                "description": e.get("shortDescription", e["displayName"]),
                "author": e["publisher"]["displayName"],
                "authorUrl": "https://marketplace.visualstudio.com/publishers/"
                + e["publisher"]["publisherName"],
                "lastUpdated": parse_date(asset["updated_at"]),
                "platform": platform,
            }


def dl_go_packages(dst_dir, vsix, json_data, dry_run, isImportant=True):
    """
    download the Go extension tools
    """

    # hacks for speed up tests
    if "NO_GO" in os.environ:
        json_data["go-tools"] = []
        return

    # set the GOPATH to download tools in the mirror directory
    go_path = (dst_dir / "go").absolute()
    go_path.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["GOPATH"] = go_path.as_posix()

    # get the list of tools
    z = zipfile.ZipFile(vsix)
    try:
        # extensions 0.16+
        js = z.read("extension/dist/goMain.js")
    except KeyError:
        # extensions -> 0.15.2
        js = z.read("extension/out/src/goTools.js")

    m = re.search(rb"allToolsInformation = ({.+?\n});\n", js, re.DOTALL)

    tools = {}
    tool = {}
    for i in m.group(1).decode().split("\n"):
        if re.match(r"'[-\w]+': {", i.strip()):
            tool = {}

        kv = re.search(r"(\w+): (.+)", i)
        if kv:
            k, v = kv.groups()
            v = v.rstrip(",")
            v = v.strip("'")
            tool[k] = v
            if k == "isImportant":
                tool[k] = bool(v)
            if k == "description":
                tools[tool["name"]] = tool
                # print("  tool detected: {} - {}".format(tool["name"], tool["description"]))

    # issue a "go get" command for each tool
    max_length = max(len(tool["importPath"]) for tool in tools.values())
    fmt = "    {importPath:%d} {description} {flag}     " % (
        ((max_length + 7) // 8) * 8 + 4
    )
    for tool in tools.values():
        flag = ["📢", "📣"][tool["isImportant"]]
        print(fmt.format(**tool, flag=flag), end="")
        sys.stdout.flush()
        if isImportant or tool["isImportant"]:
            cmd = ["go", "get", "-u", "-d", tool["importPath"]]
            if dry_run:
                rc = 0
                print(cmd)
            else:
                rc = subprocess.call(
                    cmd, env=env, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL
                )
            print([HEAVY_BALLOT_X, CHECK_MARK][rc == 0])
        else:
            print(" skipping")

    # make an archive with Go tools
    cmd = ["tar", "-czf", "go-tools.tar.gz", "go"]
    if dry_run:
        print(cmd)
    else:
        subprocess.call(cmd, cwd=dst_dir.as_posix())

        sh = dst_dir / "go-tools.sh"
        sh.write_text(
            "#!/bin/sh\n" +
            "go get \\\n  " +
            " \\\n  ".join(tool["importPath"] for tool in tools.values()) +
            "\n")
        sh.chmod(0o755)

    json_data["go-tools"] = tools


def dl_extensions(dst_dir, extensions, json_data, engine_version, dry_run, no_golang):
    """
    download or update extensions
    """

    response = get_extensions(extensions, engine_version)

    # analyze the response
    for e in response:
        # DEBUG 1
        # print(json.dumps(e, indent=4))

        # DEBUG 2
        # print("displayName             :", e["displayName"])
        # print("extensionName           :", e["extensionName"])
        # print("shortDescription        :", e["shortDescription"])
        # print("publisher.publisherName :", e["publisher"]["publisherName"])
        # print("publisher.displayName   :", e["publisher"]["displayName"])

        # for i, v in enumerate(e["versions"]):
        #     print(f"version[{i}]              :", v["version"])
        #     print(f"assetUri[{i}]             :", v["assetUri"])
        # assert len(e["versions"]) == 1
        # print()

        # unique extension identifier, like "ms-python.python"
        key = e["publisher"]["publisherName"] + "." + e["extensionName"]

        if key == CPPTOOLS_KEY:
            process_cpptools(dst_dir, json_data, e)
        else:
            version = e["versions"][0]["version"]

            json_data["extensions"][key] = {
                "version": version,
                "vsix": "vsix/" + (key + "-" + version + ".vsix"),
                "vsixAsset": e["versions"][0]["assetUri"]
                + "/Microsoft.VisualStudio.Services.VSIXPackage",
                "url": "https://marketplace.visualstudio.com/items?itemName=" + key,
                "icon": "icons/" + (key + ".png"),
                "iconAsset": f'{e["versions"][0]["assetUri"]}/Microsoft.VisualStudio.Services.Icons.Small',
                "name": e["displayName"],
                "description": e.get("shortDescription", e["displayName"]),
                "author": e["publisher"]["displayName"],
                "authorUrl": "https://marketplace.visualstudio.com/publishers/"
                + e["publisher"]["publisherName"],
                "lastUpdated": parse_date(e["versions"][0]["lastUpdated"]),
                # "platform": ""
            }

    # print(json.dumps(json_data["extensions"], indent=4))

    for key, data in json_data["extensions"].items():

        vsix = dst_dir / data["vsix"]
        icon = dst_dir / data["icon"]

        # download vsix
        if not vsix.is_file():
            if icon.is_file():
                icon.unlink()
            print(
                "{:20} {:35} {:10} {} downloading...".format(
                    *key.split("."), data["version"], HEAVY_BALLOT_X
                )
            )
            if not dry_run:
                download(data["vsixAsset"], vsix)
        else:
            print(
                "{:20} {:35} {:10} {}".format(
                    *key.split("."), data["version"], CHECK_MARK
                )
            )

        # download icon
        if not icon.is_file():
            if not dry_run:
                ok = download(data["iconAsset"], icon)
            else:
                ok = True
            if not ok:
                # default icon: { visual studio code }
                url = "https://cdn.vsassets.io/v/20180521T120403/_content/Header/default_icon.png"
                download(url, icon)

        if key == "golang.Go":
            dl_go_packages(dst_dir, vsix, json_data, dry_run)

    # write the markdown catalog file
    with open(dst_dir / "extensions.md", "w") as f:

        md = ["Icon", "Name", "Description", "Author", "Version", "Date"]

        print("|".join(md), file=f)
        print("|".join(["-" * len(i) for i in md]), file=f)

        for key, data in json_data["extensions"].items():

            def new_row(data):
                md[0] = "![{name}]({icon})".format_map(data)
                md[1] = "[{name}]({url})".format_map(data)
                md[2] = data["description"]
                md[3] = "[{author}]({authorUrl})".format_map(data)
                md[4] = "[{version}]({vsix})".format_map(data)
                md[5] = data["lastUpdated"]

                print("|".join(md), file=f)

            new_row(data)


def dl_code(dst_dir, channel="stable", revision="latest"):
    """
    download code for Linux from Microsoft debian-like repo
    """

    url = f"https://update.code.visualstudio.com/{revision}/linux-deb-x64/{channel}"
    r = requests.get(url, allow_redirects=False)
    if r.status_code != 302:
        logging.error(f"cannot get {channel} channel")
        return

    url = r.headers["Location"]
    path = urllib.parse.urlsplit(url).path.split("/")
    if len(path) != 4:
        logging.error(f"cannot parse url {url}")
        return

    commit_id = path[2]
    deb_filename = path[3]
    package = "code"
    filename = dst_dir / "code" / commit_id / deb_filename
    tag = re.search(r"_(.+)_", deb_filename).group(1)
    version = tag.split("-", 1)[0]

    if filename.is_file():
        print("{:50} {:20} {}".format(package, tag, CHECK_MARK))
    else:
        print("{:50} {:20} {} downloading...".format(package, tag, HEAVY_BALLOT_X))
        download(url, filename)

        d = filename.parent.parent / revision
        if d.is_symlink():
            d.unlink()
        d.symlink_to(commit_id, target_is_directory=True)

        d = filename.parent.parent / version
        if d.is_symlink():
            d.unlink()
        d.symlink_to(commit_id, target_is_directory=True)

    data = {}
    data["version"] = version
    data["tag"] = tag
    data["channel"] = channel
    data["commit_id"] = commit_id
    data["url"] = str(filename.relative_to(dst_dir))
    data["deb"] = deb_filename
    data["server"] = []

    for arch in ["x64", "armhf", "alpine", "arm64"]:
        package = f"server-linux-{arch}"
        url = f"https://update.code.visualstudio.com/commit:{commit_id}/{package}/{channel}"
        r = requests.get(url, allow_redirects=False)
        if r.status_code == 302:
            url = r.headers["Location"]
            path = urllib.parse.urlsplit(url).path.split("/")
            if len(path) != 4:
                continue
            filename = dst_dir / "code" / commit_id / path[3]
            data["server"].append(path[3])

            if filename.is_file():
                print("{:50} {:20} {}".format(package, version, CHECK_MARK))
            else:
                print(
                    "{:50} {:20} {} downloading...".format(
                        package, version, HEAVY_BALLOT_X
                    )
                )
                download(url, filename)

    return data


def purge(path, keep):
    """
    keep only `keep` old versions
    return the list of files removed
    """

    if re.match("vsix", path):
        pattern = re.compile(r"^([\w\-]+\.[\w\-]+)\-(\d+\.\d+\.\d+)\.vsix$")
    else:
        pattern = re.compile(r"^([\w\-]+)_(\d+\.\d+\.\d+\-\d+)_amd64\.deb$")

    files = defaultdict(lambda: [])
    for f in pathlib.Path(path).glob("**/*"):
        g = re.match(pattern, f.name)
        if not g:
            logging.warn("not matching RE: %s", f)
        else:
            version = list(map(int, re.split("[.-]", g.group(2))))
            files[g.group(1)].append((f, version))

    unlink = []
    for k, e in files.items():
        n = max(keep, 0) + 1
        for f, v in sorted(e, key=itemgetter(1), reverse=True):
            if n == 0:
                # print("UNLINK", k, v)
                unlink.append(f)
            else:
                # print("KEEP  ", k, v)
                n -= 1

    for f in unlink:
        logging.debug("unlink %s", f)
        f.unlink()

    return unlink


def download_assets(destination):
    """
    download assets (css, images, javascript)
    """

    dst_dir = pathlib.Path(destination)
    logging.debug("copy assets into %s", dst_dir)

    # src_dir = pathlib.Path(__file__).parent
    # if src_dir != dst_dir:
    #     shutil.copy2(src_dir / "index.html", dst_dir)
    #     shutil.copy2(src_dir / "get.py", dst_dir)
    #     (dst_dir / "get.py").chmod(0o755)

    shutil.copy2(pkg_resources.resource_filename(__name__, "index.html"), dst_dir)
    shutil.copy2(pkg_resources.resource_filename(__name__, "get.py"), dst_dir)
    (dst_dir / "get.py").chmod(0o755)

    if (dst_dir / "team.json").exists() is False:
        with (dst_dir / "team.json").open("w") as fd:
            fd.write("[]")

    os.chdir(dst_dir)

    # markdown-it
    download(
        "https://cdnjs.cloudflare.com/ajax/libs/markdown-it/8.4.1/markdown-it.min.js",
        "markdown-it.min.js",
    )
    download(
        "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.12.0/highlight.min.js",
        "highlight.min.js",
    )
    download(
        "https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.12.0/styles/vs2015.min.css",
        "vs2015.min.css",
    )

    # Mou/MacDown GitHub like stylesheet
    download(
        "https://raw.githubusercontent.com/gcollazo/mou-theme-github2/master/GitHub2.css",
        "GitHub2.css",
    )

    # images from VSCode homepage
    download(
        "https://code.visualstudio.com/assets/images/home-debug.svg",
        "images/home-debug.svg",
    )
    download(
        "https://code.visualstudio.com/assets/images/home-git.svg",
        "images/home-git.svg",
    )
    download(
        "https://code.visualstudio.com/assets/images/home-intellisense.svg",
        "images/home-intellisense.svg",
    )
    download(
        "https://code.visualstudio.com/assets/images/Hundreds-of-Extensions.png",
        "images/Hundreds-of-Extensions.png",
    )

    # VSCode icon as favicon
    download(
        "https://github.com/Microsoft/vscode/raw/master/resources/win32/code.ico",
        "favicon.ico",
    )


def print_conf(args):
    """
    print the configuration as a YAML file
    """

    try:
        s = subprocess.check_output(
            "code --list-extensions", shell=True, stderr=subprocess.DEVNULL
        )
        installed = set(s.decode().split())
    except subprocess.CalledProcessError:
        installed = set()

    listed = set()
    if os.path.exists(args.conf):
        conf = yaml.load(open(args.conf), Loader=yaml.BaseLoader)
        if "extensions" in conf:
            listed = set(conf["extensions"])

    conf["installed"] = list(installed)
    conf["not-installed"] = list(listed - installed)
    conf["not-listed"] = list(installed - listed)

    # sys.stdout.write("\033[1;36m")
    yaml.dump(conf, stream=sys.stdout, default_flow_style=False)
    # sys.stdout.write("\033[0m\n")


def download_code_vsix(args):
    """
    the real thing is here
    """

    json_data = {"code": {}, "extensions": {}}
    dst_dir = pathlib.Path(args.root)

    # download VSCode
    if not args.no_code:
        json_data["code"] = dl_code(dst_dir)

    # set the engine version (computed value from vscode version...)
    if args.engine:
        engine_version = ".".join((args.engine + ".0").split(".")[0:3])
    else:

        if "code" in json_data and "version" in json_data["code"]:
            engine_version = ".".join(
                json_data["code"]["version"].split(".")[0:2] + ["0"]
            )
            if engine_version == "1.29.0":
                engine_version = "1.29.1"
            logging.debug(
                "vscode engine version: %s (deduced from version %s)",
                engine_version,
                json_data["code"]["version"],
            )
        else:
            engine_version = "*"
    logging.debug("using Code engine version: %s", engine_version)

    # prepare the extension list
    extensions = list()

    # get the listed extensions
    if os.path.exists(args.conf):
        conf = yaml.load(open(args.conf), Loader=yaml.BaseLoader)
        if "extensions" in conf:
            listed = set(conf["extensions"])
            extensions = list(listed.union(extensions))
        conf = None

    # download extensions
    dl_extensions(
        dst_dir, extensions, json_data, engine_version, args.dry_run, args.no_golang
    )

    # write the JSON data file
    with open(dst_dir / "data.json", "w") as f:
        json.dump(json_data, f, indent=4)


def server(web_root, port):
    """
    run the HTTP server
    """

    import http.server
    from functools import partial

    logging.info("running HTTP server for %s port %d", web_root, port)

    if sys.version_info.major == 3 and sys.version_info.minor <= 6:
        os.chdir(web_root)
        http.server.test(HandlerClass=http.server.SimpleHTTPRequestHandler, port=port)
    else:
        handler_class = partial(
            http.server.SimpleHTTPRequestHandler, directory=web_root
        )
        http.server.test(HandlerClass=handler_class, port=port)


def main():
    """
    main function
    """

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-v", "--verbose", help="increase verbosity", action="store_true"
    )
    parser.add_argument(
        "-c", "--conf", help="configuration file", default="extensions.yaml"
    )
    parser.add_argument("--no-code", help="do not download Code", action="store_true")
    parser.add_argument(
        "--no-golang", help="do not download Go packages", action="store_true"
    )
    parser.add_argument("-e", "--engine", help="set the required engine version")
    parser.add_argument(
        "-k",
        "--keep",
        help="number of old versions to keep",
        type=int,
        metavar="N",
        nargs="?",
        const=10,
    )
    parser.add_argument(
        "-Y",
        "--yaml",
        help="output a conf file with installed extensions (and exit)",
        action="store_true",
    )
    parser.add_argument(
        "--assets", help="download css and images (and exit)", action="store_true"
    )
    parser.add_argument(
        "--no-assets",
        help="do not download css and images (and exit)",
        action="store_true",
    )
    parser.add_argument("--cache", help="enable Requests cache", action="store_true")
    parser.add_argument("-r", "--root", help="set the root directory")
    parser.add_argument("-s", "--server", help="HTTP server", action="store_true")
    parser.add_argument("-p", "--port", help="HTTP port", type=int, default=8000)
    parser.add_argument("-n", "--dry-run", help="dry run", action="store_true")

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(
            format="%(asctime)s:%(levelname)s:%(message)s",
            level=logging.DEBUG,
            datefmt="%H:%M:%S",
        )
        logging.debug("args {}".format(args))
    else:
        logging.basicConfig(
            format="%(asctime)s:%(levelname)s:%(message)s",
            level=logging.INFO,
            datefmt="%H:%M:%S",
        )

    if args.cache:
        # install a static cache (for developping and comfort reasons)
        expire_after = datetime.timedelta(hours=1)
        requests_cache.install_cache(
            "cache", allowable_methods=("GET", "POST"), expire_after=expire_after
        )
        requests_cache.core.remove_expired_responses()

    args.conf = os.path.abspath(args.conf)
    if not os.path.isfile(args.conf):
        args.conf = pkg_resources.resource_filename(__name__, "extensions.yaml")
        logging.debug(f"using default conf {args.conf}")

    if args.root is None:
        try:
            args.root = yaml.load(open(args.conf), Loader=yaml.BaseLoader)["web_root"]
        except Exception:
            args.root = "web"  # default directory
    args.root = os.path.abspath(args.root)

    if os.path.isdir(args.root) is False:
        logging.error("directory does not exist: %s", args.root)
        exit(2)

    # action 0: run http server
    if args.server:
        return server(args.root, args.port)

    # action 1: only download assets (and do nothing else)
    if args.assets:
        logging.warning("--assets is deprecated")
        return download_assets(args.root)

    # action 2: get a conf file (and do nothing else)
    if args.yaml:
        return print_conf(args)

    # action 3: download code/vsix and assets
    download_code_vsix(args)

    if args.keep is not None:
        purge("code", args.keep)
        purge("vsix", args.keep)
    else:
        purge("code", 0)
        purge("vsix", 0)

    if not args.no_assets:
        download_assets(args.root)


def win_term():
    """
    set the Windows console to understand the ANSI color codes
    """
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


if __name__ == "__main__":
    win_term()
    main()
