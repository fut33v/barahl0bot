#!/bin/sh
until python3 ./get_photos.py; do
    echo "Script 'get_photos' crashed with exit code $?.  Respawning.." >&2
    sleep 1
done

