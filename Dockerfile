FROM alpine:latest

RUN apk update \
&&  apk add --no-cache python3 \
&&  python3 -mpip install --upgrade pip

# Go tools require Go and git to run "go get" commands
RUN apk add --no-cache go git

VOLUME /app/web

WORKDIR /app

COPY . .
RUN pip3 install .

ENTRYPOINT [ "/usr/bin/vscode-dl" ]
