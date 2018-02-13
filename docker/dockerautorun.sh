#!/usr/bin/env bash

if [ ! -f ${DATA}/.setupseen ]; then
    echo "--------------------"
    echo "     Nano SETUP     "
    echo "--------------------"

    echo "This is the first time you are running this container."
    echo "Please open the /files volume and edit configuration files (in /files/data), then restart this container."

    cd ${DATA}/data/
    touch .setupseen
    cp config.ini.example config.ini
    cp settings.ini.example settings.ini
    sleep 10d
    exit 2

else
    # Start both redis servers
    nohup redis-server /files/redis-docker.conf &
    nohup redis-server /files/redisCache-docker.conf &

    python3.5 /home/Nano/nano.py > my.log
fi
