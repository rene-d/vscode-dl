#! /bin/sh

docker-compose up --build -d

# wait for mirroring
docker wait vscode_dl_sync
docker logs vscode_dl_sync

echo "Mirroring is complete. Testing installation..."

# Nota: the container has no Internet access
docker-compose exec client ./client.sh

echo "Tear down the test..."

docker-compose down
