#!/bin/sh
gzip -d "2021112021012001.tar"
pg_restore -c -U fut33v -d barahlochannel -v "2021112021012001.tar" -W
