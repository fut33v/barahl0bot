#!/bin/sh
until python3 ./get_photos.py; do
    echo "Server 'myserver' crashed with exit code $?.  Respawning.." >&2
    sleep 1
done

