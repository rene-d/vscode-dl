FROM alpine:latest

RUN apk update \
&& apk add --no-cache --virtual .build-deps g++ python3-dev libffi-dev openssl-dev \
&& apk add --no-cache  --update python3 py-pip \
&& pip3 install --upgrade pip setuptools

# Go tools require Go and git to run "go get" commands
RUN apk add --no-cache go git

VOLUME /app/web

WORKDIR /app

COPY . .
RUN pip3 install .

ENTRYPOINT [ "/usr/bin/vscode-dl" ]
