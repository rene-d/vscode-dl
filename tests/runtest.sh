#! /bin/sh

docker-compose up --build -d

# wait for mirroring
docker wait vscode_dl_sync
docker logs vscode_dl_sync

docker-compose exec client ./client.sh

docker-compose down
