#!/bin/bash

# Where the Avahi Deamon folder is located
AVAHI_PATH="/etc/avahi/avahi-daemon.conf"

# Schlüssel, nach dem gesucht wird
KEY="host-name"

if [[ -f "$AVAHI_PATH" ]]; then
    VALUE=$(grep -E "^\s*host-name\s*=" "$CONFIG_FILE" | sed 's/.*=\s*//')

    if [[ "$VALUE" == "t250" ]]; then
        echo "t250"
    fi
else
    echo "Konfigurationsdatei nicht gefunden: $CONFIG_FILE"
    exit 1
fi