#! /usr/bin/env python3

import argparse
import subprocess
import re
import os
import requests
import pprint
import datetime
import email.utils
import dateutil.parser
import yaml


check_mark = "\033[32m\N{check mark}\033[0m"            # ✔
heavy_ballot_x = "\033[31m\N{heavy ballot x}\033[0m"    # ✘



my_extensions = ['ms-vscode.cpptools',
                 'ms-python.python',
                 'MS-CEINTL.vscode-language-pack-fr',
                 'vector-of-bool.cmake-tools']


def reorder_extensions(f):
    if f in my_extensions:
        return my_extensions.index(f)
    return len(my_extensions) + 1


def my_parsedate(text):
    return datetime.datetime(*email.utils.parsedate(text)[:6])


def download(url, file):
    r = requests.get(url, allow_redirects=True)
    if r.status_code == 200:
        os.makedirs(os.path.dirname(file), exist_ok=True)
        with open(file, 'wb') as f:
            f.write(r.content)
        if r.headers.get('last-modified'):
            d = my_parsedate(r.headers['last-modified'])
            ts = d.timestamp()
            os.utime(file, (ts, ts))
        return True
    else:
        print(heavy_ballot_x, r.status_code)
        return False


parser = argparse.ArgumentParser()
parser.add_argument("--scan", help="scan and download installed extensions", action='store_true')
parser.add_argument("-x", help="scan and download installed extensions", action='store_true')
parser.add_argument("-v", "--verbose", help="increase verbosity", action='store_true')
args = parser.parse_args()

if args.scan:
    s = subprocess.check_output("code --list-extensions --show-versions", shell=True)
    # print(s.decode())
    for publisher, extension_name, version in re.findall(r'(.*)\.(.*)@(.*)', s.decode()):

        #url = f"https://marketplace.visualstudio.com/_apis/public/gallery/publishers/{publisher}/vsextensions/{extension_name}/{version}/vspackage"
        url = f"https://{publisher}.gallery.vsassets.io/_apis/public/gallery/publisher/{publisher}/extension/{extension_name}/{version}/assetbyname/Microsoft.VisualStudio.Services.VSIXPackage"
        vsix = f"vsix/{publisher}.{extension_name}-{version}.vsix"

        if os.path.exists(vsix) is False:
            cmd = f"curl -s -o '{vsix}' '{url}'"
            print("{:20} {:35} {:10} {} : downloading...".format(publisher, extension_name, version, heavy_ballot_x))
            subprocess.call(cmd, shell=True)
        else:
            print("{:20} {:35} {:10} {}".format(publisher, extension_name, version, check_mark))


if args.x:

    # get installed extensions
    s = subprocess.check_output("code --list-extensions", shell=True)
    installed = set(s.decode().split())

    # get the listed extensions
    if os.path.exists("extensions.yaml"):
        conf = yaml.load(open("extensions.yaml"))
        if 'extensions' in conf:
            listed = set(conf['extensions'])
        conf = None

    extensions = list(installed.union(listed))

    # markdown skeliton
    md = []
    md.append(['Logo', 'Nom', 'Description', 'Auteur', 'Version', 'Date'])
    md.append(['-' * len(i) for i in md[0]])

    # prepare the REST query
    data = {
        "filters": [
            {
                "criteria": [
                    { "filterType": 8, "value": "Microsoft.VisualStudio.Code" },
                    { "filterType": 12, "value": "4096" },
                ],
            }
        ],
        "flags": 0x200 + 0x80       # IncludeLatestVersionOnly IncludeAssetUri
    }                               # cf. vs/platform/extensionManagement/node/extensionGalleryService.ts

    for ext in extensions:
        data['filters'][0]['criteria'].append({'filterType': 7, 'value': ext})

    headers = {'Content-type': 'application/json', 'Accept': 'application/json;api-version=3.0-preview.1'}

    # query the gallery
    req = requests.post("https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery", json=data, headers=headers)
    res = req.json()
    if args.verbose:
        pprint.pprint(res)

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

            key =  e['publisher']['publisherName'] + '.' + e['extensionName']
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
            row.append(str(d))

            md.append(row)



            if not os.path.exists(vsix):
                if os.path.exists(icon):
                    os.unlink(icon)

                url = e['versions'][0]['assetUri'] + '/Microsoft.VisualStudio.Services.VSIXPackage'

                print("{:20} {:35} {:10} {} downloading...".format(e['publisher']['publisherName'], e['extensionName'], version, heavy_ballot_x))

                download(url, vsix)
            else:
                print("{:20} {:35} {:10} {}".format(e['publisher']['publisherName'], e['extensionName'], version, check_mark))


            if key == "ms-vscode.cpptools":
                for platform in ['linux', 'win32', 'osx', 'linux32']:
                    url = f"https://github.com/Microsoft/vscode-cpptools/releases/download/{version}/cpptools-{platform}.vsix"
                    vsix = f'vsix/{key}-{platform}-{version}.vsix'
                    if not os.path.exists(vsix):
                        print("{:20} {:35} {:10} {} downloading...".format("", "cpptools-" + platform, version, heavy_ballot_x))
                        download(url, vsix)
                    else:
                        print("{:20} {:35} {:10} {}".format("", "cpptools-" + platform, version, check_mark))


            if not os.path.exists(icon):
                os.makedirs("icons", exist_ok=True)
                url = e['versions'][0]['assetUri'] + '/Microsoft.VisualStudio.Services.Icons.Small'
                ok = download(url, icon)
                if not ok:
                    # default icon: { visual studio code }
                    url = 'https://cdn.vsassets.io/v/20180521T120403/_content/Header/default_icon.png'
                    download(url, icon)


    with open("README.md", "w") as f:
        for i in md:
            print('|'.join(i), file=f)
