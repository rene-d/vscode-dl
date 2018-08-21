#! /usr/bin/env python3
# rene-d 2018

import sys
import argparse
import subprocess
import re
import os
import requests
import requests_cache
import datetime
import email.utils
import dateutil.parser
import yaml
import bz2
import json
import logging
import pathlib
from collections import defaultdict
from operator import itemgetter


# be a little more visual like npm ;-)
check_mark = "\033[32m\N{check mark}\033[0m"            # ✔
heavy_ballot_x = "\033[31m\N{heavy ballot x}\033[0m"    # ✘


# logger options
if sys.stdout.isatty():
    logging.addLevelName(logging.DEBUG, "\033[0;32m%s\033[0m" % logging.getLevelName(logging.DEBUG))
    logging.addLevelName(logging.INFO, "\033[1;33m%s\033[0m" % logging.getLevelName(logging.INFO))
    logging.addLevelName(logging.WARNING, "\033[1;35m%s\033[1;0m" % logging.getLevelName(logging.WARNING))
    logging.addLevelName(logging.ERROR, "\033[1;41m%s\033[1;0m" % logging.getLevelName(logging.ERROR))


def my_parsedate(text):
    """ parse date from http headers response
    """
    return datetime.datetime(*email.utils.parsedate(text)[:6])


def download(url, file):
    """ download a file and set last modified time
    """
    with requests_cache.disabled():
        r = requests.get(url, allow_redirects=True)
    if r.status_code == 200:
        d = os.path.dirname(file)
        if d != "":
            os.makedirs(d, exist_ok=True)
        with open(file, 'wb') as f:
            f.write(r.content)
        if r.headers.get('last-modified'):
            d = my_parsedate(r.headers['last-modified'])
            ts = d.timestamp()
            os.utime(file, (ts, ts))
        return True
    else:
        print(heavy_ballot_x, r.status_code, url)
        return False


# cf. vs/platform/extensionManagement/node/extensionGalleryService.ts

class FilterType:
    ExtensionId = 4
    ExtensionName = 7
    Target = 8
    ExcludeWithFlags = 12


class Flags:
    IncludeVersions = 0x1
    IncludeFiles = 0x2
    IncludeVersionProperties = 0x10
    IncludeInstallationTargets = 0x40
    IncludeAssetUri = 0x80
    IncludeStatistics = 0x100
    IncludeLatestVersionOnly = 0x200
    Unpublished = 0x1000


def is_engine_valid(engine, extension):
    """ check if extension version <= engine version
    Nota: the sematic follows https://semver.org
    """

    if engine == '*':
        return True
    if extension[0] != '^':
        # if version doesn't begin with ^, I don't know how to handle it
        logging.error("unknown engine version semantic: %s", extension)
        return False
    a = list(map(int, engine.split('.')))
    b = list(map(int, extension[1:].split('.')))
    return a >= b


def get_extensions(extensions, vscode_engine):
    """ retrieve from server the extension list with engine version validated
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
                    {"filterType": FilterType.Target, "value": "Microsoft.VisualStudio.Code"},
                    {"filterType": FilterType.ExcludeWithFlags, "value": str(Flags.Unpublished)},
                ],
            }
        ],
        "flags": Flags.IncludeLatestVersionOnly + Flags.IncludeAssetUri + Flags.IncludeVersionProperties
    }
    for ext in sorted(extensions):
        data['filters'][0]['criteria'].append({'filterType': FilterType.ExtensionName, 'value': ext})

    headers = {'Content-type': 'application/json', 'Accept': 'application/json;api-version=3.0-preview.1'}

    # query the gallery
    logging.info("query IncludeLatestVersionOnly")
    req = requests.post("https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery",
                        json=data, headers=headers)
    res = req.json()

    # analyze the response
    not_compatible = []
    result = []

    if 'results' in res and 'extensions' in res['results'][0]:
        for e in res['results'][0]['extensions']:

            # print(e['displayName'], e['shortDescription'], e['publisher']['displayName'])

            for v in e['versions']:
                # print("", v['version'])
                # print(v['assetUri'] + '/Microsoft.VisualStudio.Services.VSIXPackage')
                pass

            for p in e['versions'][0]['properties']:
                if p['key'] == 'Microsoft.VisualStudio.Code.Engine':
                    # print("", p['key'], p['value'])
                    if is_engine_valid(vscode_engine, p['value']):
                        break
            else:
                logging.warning("KO: '%s | %s | %s | %s",
                                e['displayName'], e['shortDescription'],
                                e['publisher']['displayName'], e['versions'][0]['version'])
                # we will look for a suitable version later
                not_compatible.append(e['extensionId'])
                continue

            logging.debug("OK: '%s | %s | %s | %s",
                          e['displayName'], e['shortDescription'],
                          e['publisher']['displayName'], e['versions'][0]['version'])
            result.append(e)

    if len(not_compatible) == 0:
        # we have all we need
        return result

    # prepare the second query
    data = {
        "filters": [
            {
                "criteria": [
                    {"filterType": FilterType.Target, "value": "Microsoft.VisualStudio.Code"},
                    {"filterType": FilterType.ExcludeWithFlags, "value": str(Flags.Unpublished)},
                ],
            }
        ],
        "flags": Flags.IncludeVersions + Flags.IncludeAssetUri + Flags.IncludeVersionProperties
    }
    for id in not_compatible:
        data['filters'][0]['criteria'].append({'filterType': FilterType.ExtensionId, 'value': id})

    # query the gallery
    logging.info("query IncludeVersions")
    req = requests.post("https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery",
                        json=data, headers=headers)
    res = req.json()

    if 'results' in res and 'extensions' in res['results'][0]:
        for e in res['results'][0]['extensions']:

            logging.debug("analyze %s | %s | %s",
                          e['displayName'], e['shortDescription'], e['publisher']['displayName'])

            # find the greatest version compatible with our vscode engine
            max_vernum = []
            max_version = None
            for v in e['versions']:
                engine = "?"
                for p in v['properties']:
                    if p['key'] == 'Microsoft.VisualStudio.Code.Engine':
                        engine = p['value']
                is_valid = is_engine_valid(vscode_engine, engine)
                logging.debug("found version %s engine %s : %s", v['version'], engine, is_valid)
                if is_valid:
                    # well, it seems that versions are sorted latest first
                    # since it's not sure, I prefer searching for the greatest version number
                    vernum = list(map(int, v['version'].split('.')))
                    if vernum > max_vernum:
                        max_vernum = vernum
                        max_version = v

            if max_version:
                logging.debug("version %s is the best suitable choice", max_version['version'])
                e['versions'] = [max_version]
            else:
                logging.error("no suitable version found")

            result.append(e)

    return result


def dl_extensions(extensions, json_data, engine_version="1.25.0"):
    """ download or update extensions
    """

    response = get_extensions(extensions, engine_version)

    # markdown skeliton
    md = []
    md.append(['Icon', 'Name', 'Description', 'Author', 'Version', 'Date'])
    md.append(['-' * len(i) for i in md[0]])

    # analyze the response
    for e in response:

        # print(e['displayName'])
        # print(e['shortDescription'])
        # print(e['publisher']['displayName'])
        # for v in e['versions']:
        #     print(v['version'])
        #     print(v['assetUri'] + '/Microsoft.VisualStudio.Services.VSIXPackage')
        # print()

        row = []

        key = e['publisher']['publisherName'] + '.' + e['extensionName']
        version = e['versions'][0]['version']
        vsix = 'vsix/' + key + '-' + version + '.vsix'
        icon = 'icons/' + key + '.png'

        # column 1: icon
        row.append("![{}]({})".format(e['displayName'], icon))

        row.append("[{}]({})".format(
            e['displayName'],
            'https://marketplace.visualstudio.com/items?itemName=' + key))

        # column 2: description
        row.append(e['shortDescription'])

        # column 3: author
        row.append('[{}]({})'.format(
            e['publisher']['displayName'],
            'https://marketplace.visualstudio.com/publishers/' + e['publisher']['publisherName']))

        # column 4: version
        row.append("[{}]({})".format(e['versions'][0]['version'], vsix))

        # column 5: last update time
        d = dateutil.parser.parse(e['versions'][0]['lastUpdated'])
        row.append(d.strftime("%Y/%m/%d&nbsp;%H:%M:%S"))

        md.append(row)

        # download the extension
        if not os.path.exists(vsix):
            if os.path.exists(icon):
                os.unlink(icon)

            url = e['versions'][0]['assetUri'] + '/Microsoft.VisualStudio.Services.VSIXPackage'

            print("{:20} {:35} {:10} {} downloading...".format(
                e['publisher']['publisherName'], e['extensionName'], version, heavy_ballot_x))
            download(url, vsix)
        else:
            print("{:20} {:35} {:10} {}".format(e['publisher']['publisherName'], e['extensionName'], version, check_mark))

        if json_data:
            json_data['extensions'][key] = {'version': version, 'vsix': vsix}

        # download the supplementary files for C/C++ extension
        if key == "ms-vscode.cpptools":
            # platforms = ['linux', 'win32', 'osx', 'linux32']
            platforms = ['linux']
            for platform in platforms:
                url = f"https://github.com/Microsoft/vscode-cpptools/releases/download/v{version}/cpptools-{platform}.vsix"
                vsix = f'vsix/{key}-{platform}-{version}.vsix'
                if not os.path.exists(vsix):
                    print("{:20} {:35} {:10} {} downloading...".format("", "cpptools-" + platform, version, heavy_ballot_x))
                    ok = download(url, vsix)
                else:
                    print("{:20} {:35} {:10} {}".format("", "cpptools-" + platform, version, check_mark))
                    ok = True

                if ok:
                    d = datetime.datetime.fromtimestamp(os.stat(vsix).st_mtime).strftime("%Y/%m/%d&nbsp;%H:%M:%S")

                    row = [f"![{e['displayName']}]({icon})",                                # icon
                           f"[vscode-cpptools](https://github.com/Microsoft/vscode-cpptools/releases/)",     # name
                           f"{key}-{platform}",                                             # description
                           "[Microsoft](https://github.com/Microsoft/vscode-cpptools)",     # author
                           f"[{version}]({vsix})",                                          # version/download link
                           f"{d}"]                                                          # date
                    md.append(row)

        # download icon
        if not os.path.exists(icon):
            os.makedirs("icons", exist_ok=True)
            url = e['versions'][0]['assetUri'] + '/Microsoft.VisualStudio.Services.Icons.Small'
            ok = download(url, icon)
            if not ok:
                # default icon: { visual studio code }
                url = 'https://cdn.vsassets.io/v/20180521T120403/_content/Header/default_icon.png'
                download(url, icon)

    # write the markdown catalog file
    with open("extensions.md", "w") as f:
        for i in md:
            print('|'.join(i), file=f)


def dl_code(json_data):
    """ download code for Linux from Microsoft debian-like repo
    """

    repo = "http://packages.microsoft.com/repos/vscode"
    url = f"{repo}/dists/stable/main/binary-amd64/Packages.bz2"
    r = requests.get(url)
    if r.status_code == 200:
        data = bz2.decompress(r.content).decode('utf-8')

        packages = []
        sect = {}
        key, value = None, None

        def _add_value():                       # save key/value into current section
            nonlocal key, value, sect
            if key and value:
                sect[key] = value

                if key == 'version':
                    # set up a list that should be in the same order as version numbers
                    sect['_version'] = list(map(int, re.split(r'[.-]', value)))

                key = value = None

        def _add_sect():
            nonlocal sect, packages
            _add_value()
            if len(sect) != 0:
                packages.append(sect)
                sect = {}                       # start a new section

        for line in data.split('\n'):
            if line == '':                      # start a new section
                _add_sect()
            elif line[0] == ' ':                # continue a key/value
                if value is not None:
                    value += line
            else:                               # start a new key/value
                _add_value()
                key, value = line.split(':', maxsplit=1)
                key = key.lower()               # make key always lowercase
                value = value.lstrip()

        _add_sect()                             # flush section if any

        packages.sort(key=lambda x: x['_version'], reverse=True)

        # for package in ['code', 'code-insiders']:
        for package in ['code']:
            latest = None
            for p in packages:
                if p['package'] == package:
                    latest = p
                    break

            if latest:
                filename = latest['filename']
                url = f"{repo}/{filename}"
                deb_filename = os.path.basename(filename)
                filename = os.path.join("code", deb_filename)

                if os.path.exists(filename):
                    print("{:50} {:20} {}".format(latest['package'], latest['version'], check_mark))
                else:
                    print("{:50} {:20} {} downloading...".format(latest['package'], latest['version'], heavy_ballot_x))
                    download(url, filename)

                if json_data:
                    json_data[package] = {}
                    json_data[package]['version'] = latest['version'].split('-', 1)[0]
                    json_data[package]['url'] = filename
                    json_data[package]['deb'] = deb_filename


def purge(path, keep):
    """ keep only `keep` old versions
    return the list of files removed
    """

    if re.match('vsix', path):
        pattern = re.compile(r'^([\w\-]+\.[\w\-]+)\-(\d+\.\d+\.\d+)\.vsix$')
    else:
        pattern = re.compile(r'^([\w\-]+)_(\d+\.\d+\.\d+\-\d+)_amd64\.deb$')

    files = defaultdict(lambda: [])
    for f in pathlib.Path(path).glob('**/*'):
        g = re.match(pattern, f.name)
        if not g:
            logging.warn("not matching RE: %s", f)
        else:
            version = list(map(int, re.split('[.-]', g.group(2))))
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


def download_assets():
    """ download assets (css, images, javascript)
    """

    # markdown-it
    download("https://cdnjs.cloudflare.com/ajax/libs/markdown-it/8.4.1/markdown-it.min.js", "markdown-it.min.js")
    download("https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.12.0/highlight.min.js", "highlight.min.js")
    download("https://cdnjs.cloudflare.com/ajax/libs/highlight.js/9.12.0/styles/vs2015.min.css", "vs2015.min.css")

    # Mou/MacDown GitHub like stylesheet
    download("https://raw.githubusercontent.com/gcollazo/mou-theme-github2/master/GitHub2.css", "GitHub2.css")

    # images from VSCode homepage
    download("https://code.visualstudio.com/assets/images/home-debug.svg", "images/home-debug.svg")
    download("https://code.visualstudio.com/assets/images/home-git.svg", "images/home-git.svg")
    download("https://code.visualstudio.com/assets/images/home-intellisense.svg", "images/home-intellisense.svg")
    download("https://code.visualstudio.com/assets/images/Hundreds-of-Extensions.png", "images/Hundreds-of-Extensions.png")

    # VSCode icon as favicon
    download("https://github.com/Microsoft/vscode/raw/master/resources/win32/code.ico", "favicon.ico")


def print_conf(args):
    """ print the configuration as a YAML file
    """

    s = subprocess.check_output("code --list-extensions", shell=True)
    installed = set(s.decode().split())

    listed = set()
    if os.path.exists(args.conf):
        conf = yaml.load(open(args.conf))
        if 'extensions' in conf:
            listed = set(conf['extensions'])

    conf['installed'] = list(installed)
    conf['not-installed'] = list(listed - installed)
    conf['not-listed'] = list(installed - listed)

    # sys.stdout.write("\033[1;36m")
    yaml.dump(conf, stream=sys.stdout, default_flow_style=False)
    # sys.stdout.write("\033[0m\n")


def download_code_vsix(args):
    """ the real thing here
    """

    json_data = {'code': {}, 'extensions': {}}

    # download VSCode
    dl_code(json_data)
    print()

    # prepare the extension list
    extensions = list()

    # get the listed extensions
    if os.path.exists(args.conf):
        conf = yaml.load(open(args.conf))
        if 'extensions' in conf:
            listed = set(conf['extensions'])
            extensions = list(listed.union(extensions))
        conf = None

    # get installed extensions if asked
    if args.installed:
        s = subprocess.check_output("code --list-extensions", shell=True)
        installed = set(s.decode().split())
        extensions = list(installed.union(extensions))

    # set the engine version (computed value from vscode version...)
    if args.engine:
        engine_version = ".".join((args.engine + ".0").split('.')[0:3])
        logging.info("set vscode engine version: %s", engine_version)
    else:
        # # from the installed vscode
        # s = subprocess.run("code --version 2>/dev/null", shell=True, stdout=subprocess.PIPE).stdout
        # if s != "":
        #     ver = s.decode().split('\n')[0]
        #     logging.debug("installed vscode version: %s", ver)
        #     engine_version = ".".join(map(str, list(map(int, ver.split('.')))[0:2] + [0]))
        #     logging.debug("computed vscode engine version: %s", engine_version)

        if 'code' in json_data and 'version' in json_data['code']:
            engine_version = ".".join(json_data['code']['version'].split('.')[0:2] + ['0'])
            logging.info("vscode engine version: %s (deduced from version %s)",
                         engine_version, json_data['code']['version'])
        else:
            engine_version = "*"

    # download extensions
    dl_extensions(extensions, json_data, engine_version)

    # write the JSON data file
    with open("code.json", "w") as f:
        json.dump(json_data, f, indent=4)


def main():
    """ main function
    """

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase verbosity", action='store_true')
    parser.add_argument("-f", "--conf", help="configuration file", default="extensions.yaml")
    parser.add_argument("-i", "--installed", help="scan installed extensions", action='store_true')
    parser.add_argument("-e", "--engine", help="set the required engine version")
    parser.add_argument("-k", "--keep", help="number of old versions to keep", type=int, metavar='N', nargs='?', const=0)
    parser.add_argument("-Y", "--yaml", help="output a conf file with installed extensions (and exit)", action='store_true')
    parser.add_argument("--assets", help="download css and images (and exit)", action='store_true')
    parser.add_argument("--no-cache", help="disable Requests cache", action='store_true')
    parser.add_argument("--clear-cache", help="clear Requests cache", action='store_true')

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.DEBUG, datefmt='%H:%M:%S')
    else:
        logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s', level=logging.ERROR, datefmt='%H:%M:%S')

    if not args.no_cache:
        # install a static cache (for developping and comfort reasons)
        expire_after = datetime.timedelta(hours=1)
        requests_cache.install_cache('cache', allowable_methods=('GET', 'POST'), expire_after=expire_after)
        requests_cache.core.remove_expired_responses()

    if args.clear_cache:
        requests_cache.clear()

    # action 1: download assets (and do nothing else)
    if args.assets:
        download_assets()
        exit(0)

    # action 2: get a conf file (and do nothing else)
    if args.yaml:
        print_conf(args)
        exit(0)

    # action 3: download code/vsix
    download_code_vsix(args)
    if args.keep is not None:
        purge("code", args.keep)
        purge("vsix", args.keep)


def win_term():
    """ set the Windows console to understand the ANSI color codes
    """
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


if __name__ == '__main__':
    win_term()
    main()
