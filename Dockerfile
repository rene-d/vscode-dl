FROM alpine:latest

RUN apk update \
&&  apk add --no-cache python3 \
&&  cd /app \
&&  python3 -mpip install --upgrade pip \
&&  python3 -mpip install -r requirements.txt

# Go tools require Go and git to run "go get" commands
RUN apk add --no-cache go git

VOLUME /app/web

WORKDIR /app

COPY . .

ENTRYPOINT [ "/app/vscode-dl.py" ]
