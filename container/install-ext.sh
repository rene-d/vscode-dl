#! /usr/bin/env bash

if [ ! -f /.dockerenv ]; then
    echo 2>&1 "Cannot be run outside a container"
    exit 2
fi

# MIRROR_URL=http://mirror/vscode
# COMMIT_ID=$(ls /root/.vscode-server/bin/)

if [ -z "${MIRROR_URL}" -o -z "${COMMIT_ID}" ]; then
    echo 2>&1 "Missing environment variables"
    exit 2
fi

mapfile -t extensions < <(curl -skL ${MIRROR_URL}/data.json | jq --raw-output  '.extensions | ( keys[] as $k | "\($k) \(.[$k] | .vsix)")')

for ext in "${extensions[@]}"; do
    ext=(${ext})
    name=${ext[0]}

    for i; do
        if [ $i = $name ]; then
            echo "********************************* $name *********************************"
            dl_vsix=${MIRROR_URL}/${ext[1]}
            vsix=$(basename ${ext[1]})
            curl -skL -o /tmp/$vsix $dl_vsix
            /root/.vscode-server/bin/$COMMIT_ID/server.sh --install-extension /tmp/$vsix
            rm /tmp/$vsix
        fi
     done
done

# extensions should be in .vscode-server
mv /root/.vscode-remote/* /root/.vscode-server/
