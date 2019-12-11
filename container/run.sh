#! /bin/sh

dist=${1:-alpine}

COMMIT_ID=$(code --version | sed -n 2p)
MIRROR_URL=$(code-tool --mirror-url)

docker build -t vscode --build-arg COMMIT_ID=${COMMIT_ID} --build-arg MIRROR_URL=${MIRROR_URL} -f Dockerfile.$dist .


docker run --rm -ti --name vscode vscode bash -l

