#! /bin/bash

which python3 >/dev/null || (echo "Python3 is required"; exit 2)
cd "$(dirname $0)"

code=($(python3 -c "import json;c=json.load(open('data.json'))['code'];print(c['tag'],c['url'])"))
version=${code[0]}
deb="${code[1]}"
if [ "$(dpkg -s code | grep -o '^Version: .*$')" != "Version: ${version}" ]; then
    sudo dpkg -i "${deb}"
else
    echo "Visual Studio Code already in version ${version}"
fi

python3 ./update-extensions.py
