#!/bin/bash

# Build pre-configured docker image
docker build -t elicast-server . > /dev/null

if [ ! -d $(pwd)/db ]; then
    echo "Cannot fild '$(pwd)/db' directory!"
    exit 1
fi

# Run docker image
# -v /tmp:/tmp : to pass source code in code controller
# -v /var/run/docker.sock:/var/run/docker.sock : to execute docker commands in the server
# -v $(pwd)/db:/elicast-server-wdir/db/ : to access DB inside of the container
docker run \
    -p ${HTTP_PORT:-8080}:8080 \
    -v /tmp:/tmp \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v $(pwd)/db:/elicast-server-wdir/db/ \
    -e CONFIG_PATH \
    elicast-server \
    gunicorn \
        server:webserver.app \
        -k aiohttp.worker.GunicornWebWorker \
        -b :8080 \
        -w 2 \
        --access-logfile -