#!/bin/sh
FNAME=`date "+%Y%d%Y%H%M%S"`.tar
echo $FNAME
/usr/bin/pg_dump  -Ft -f/home/fut33v/backup/$FNAME barahlochannel
gzip /home/fut33v/backup/$FNAME
FNAMETARGZ=/home/fut33v/backup/$FNAME.gz
python3 /home/fut33v/barahl0bot/send_file.py /home/fut33v/barahl0bot/barahlochannel.json $FNAMETARGZ barahlochannel_error
