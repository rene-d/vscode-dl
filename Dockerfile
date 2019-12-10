FROM alpine:latest

COPY . /app/

RUN apk update \
&&  apk add --no-cache python3 \
&&  cd /app \
&&  python3 -mpip install --upgrade pip \
&&  python3 -mpip install -r requirements.txt

RUN apk add --no-cache go git

VOLUME /app/web

WORKDIR /app

ENTRYPOINT [ "/app/vscode-dl.py" ]
