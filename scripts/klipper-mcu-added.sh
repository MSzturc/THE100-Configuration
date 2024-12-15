#!/bin/sh
logfile="/var/log/theos.log"

if [ -e /tmp/printer ]; then
    echo "RESTART" > /tmp/printer
fi
touch "$logfile"
chmod 664 "$logfile"
echo "$(date +"%Y-%m-%d %T"): MCU Detected" >> "$logfile"