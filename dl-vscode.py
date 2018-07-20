#! /usr/bin/env python3
# rene-d 2018

import sys
import argparse
import subprocess
import re
import os
import requests
import datetime
import email.utils
import dateutil.parser
import yaml
import bz2
import json


# be a little more visual like npm ;-)
check_mark = "\033[32m\N{check mark}\033[0m"            # ✔
heavy_ballot_x = "\033[31m\N{heavy ballot x}\033[0m"    # ✘


def my_parsedate(text):
    """ parse date from http headers response """
    return datetime.datetime(*email.utils.parsedate(text)[:6])


def download(url, file):
    """ download a file and set last modified time """
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


def dl_extensions(extensions, json_data):
    """ download or update extensions """

    # markdown skeliton
    md = []
    md.append(['Logo', 'Nom', 'Description', 'Auteur', 'Version', 'Date'])
    md.append(['-' * len(i) for i in md[0]])

    # prepare the REST query
    data = {
        "filters": [
            {
                "criteria": [
                    {"filterType": 8, "value": "Microsoft.VisualStudio.Code"},
                    {"filterType": 12, "value": "4096"},
                ],
            }
        ],
        "flags": 0x200 + 0x80       # IncludeLatestVersionOnly IncludeAssetUri
    }                               # cf. vs/platform/extensionManagement/node/extensionGalleryService.ts

    for ext in extensions:
        data['filters'][0]['criteria'].append({'filterType': 7, 'value': ext})

    headers = {'Content-type': 'application/json', 'Accept': 'application/json;api-version=3.0-preview.1'}

    # query the gallery
    req = requests.post("https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery",
                        json=data, headers=headers)
    res = req.json()
    # if args.verbose: pprint.pprint(res)

    # analyze the response
    if 'results' in res and 'extensions' in res['results'][0]:
        for e in res['results'][0]['extensions']:

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

            # colonne 1: icône + nom avec lien
            row.append("![{}]({})".format(e['displayName'], icon))

            row.append("[{}]({})".format(
                e['displayName'],
                'https://marketplace.visualstudio.com/items?itemName=' + key))

            # colonne 2: description
            row.append(e['shortDescription'])

            # colonne 3: auteur
            row.append('[{}]({})'.format(
                e['publisher']['displayName'],
                'https://marketplace.visualstudio.com/publishers/' + e['publisher']['publisherName']))

            # colonne 4: version
            row.append("[{}]({})".format(e['versions'][0]['version'], vsix))

            # colonne 5: date de mise à jour
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

                        row = [f"![{e['displayName']}]({icon})",                             # icon
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
    """ download code from Microsoft debian-like repo """

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
                    # crée une chaîne qui devrait être l'ordre des numéros de version
                    sect['_version'] = '|'.join(x.rjust(16, '0') if x.isdigit() else x.ljust(16)
                                                for x in re.split(r'\W', value))

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

        latest = None
        for p in packages:
            if p['package'] == 'code':
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
                json_data['code']['version'] = latest['version'].split('-', 1)[0]
                json_data['code']['url'] = filename
                json_data['code']['deb'] = deb_filename


def main():
    """ main function """

    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--verbose", help="increase verbosity", action='store_true')
    parser.add_argument("-f", "--conf", help="configuration file", default="extensions.yaml")
    parser.add_argument("-i", "--installed", help="scan installed extensions", action='store_true')
    parser.add_argument("--assets", help="download css and images", action='store_true')

    args = parser.parse_args()

    # download assets
    if args.assets:
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

        exit(0)

    json_data = {'code': {}, 'extensions': {}}

    # download VSCode
    dl_code(json_data)
    print()

    # download extensions
    extensions = list()

    # get the listed extensions
    if os.path.exists(args.conf):
        conf = yaml.load(open(args.conf))
        if 'extensions' in conf:
            listed = set(conf['extensions'])
            extensions = list(listed.union(extensions))
        conf = None

    if args.installed:
        # get installed extensions
        s = subprocess.check_output("code --list-extensions", shell=True)
        installed = set(s.decode().split())

        if args.verbose:
            conf = yaml.load(open(args.conf))
            conf['installed'] = list(installed)
            conf['not-installed'] = list(listed - installed)
            conf['not-listed'] = list(installed - listed)
            sys.stdout.write("\033[1;36m")
            yaml.dump(conf, stream=sys.stdout, default_flow_style=False)
            sys.stdout.write("\033[0m\n")

        extensions = list(installed.union(extensions))

    dl_extensions(extensions, json_data)

    with open("code.json", "w") as f:
        json.dump(json_data, f, indent=4)


if __name__ == '__main__':
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
