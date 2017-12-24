#!/usr/bin/env bash

if [ ! -f /data/.firststart ]; then
    echo "--------------------"
    echo "     Nano SETUP     "
    echo "--------------------"

    echo "This is the first time you are running this container."
    echo "Please open the volume and edit configuration files, then start this container again."

    cd /data/data/
    touch .firststart
    cp config.ini.example config.ini
    cp settings.ini.example settings.ini
    exit 2

else
    python3.5 /home/Nano/nano.py > my.log
fi
