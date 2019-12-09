#! /bin/sh

docker-compose up --build -d

docker wait test_sync_1
docker logs test_sync_1

docker-compose exec client ./tests.sh

docker-compose down
