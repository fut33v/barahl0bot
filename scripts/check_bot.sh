#!/bin/bash

# That script checks is script for NovgorodWeatherBot running, if not, it runs it
# $1 - is directory with NovgorodWeatherBot script

SCRIPT_DIR=$1
echo $1 and $SCRIPT_DIR
SCRIPT_NAME="novgorod_weather_bot.py"
REGEXP_FOR_CHECK="[n]ovgorod_weather_bot.py"

check_bot=`ps aux | grep $REGEXP_FOR_CHECK | wc -l`

if [ $check_bot -gt 0 ] 
    then
        echo Found $check_bot process\[es\] with regexp: \"$REGEXP_FOR_CHECK\"
    exit 0
fi

echo Not found bot process with regexp $REGEXP_FOR_CHECK

echo Now cd to $SCRIPT_DIR and run $SCRIPT_NAME
cd $SCRIPT_DIR
python $SCRIPT_NAME
