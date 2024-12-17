#!/bin/bash

# Where this script is located
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR"/utils.sh

# Paths to the configuration file and printer configuration
AVAHI_PATH="/etc/avahi/avahi-daemon.conf"
PRINTER_CFG="$(user_dir)/printer_data/config/printer.cfg"
CONFIG_DIR="$(user_dir)/printer_data/config/config"

# Check if PRINTER_CFG already exists
if [[ -f "$PRINTER_CFG" ]]; then
    info "Printer configuration file already exists. No changes made."
    exit 0
else
    info "Printer configuration file not found. Checking Avahi configuration file..."
fi

# Check if the Avahi configuration file exists
if [[ -f "$AVAHI_PATH" ]]; then
    debug "Avahi configuration file found at $AVAHI_PATH."

    # Extract the value of host-name and remove whitespace
    VALUE=$(grep -E "^\s*host-name\s*=" "$AVAHI_PATH" | sed -E 's/.*=\s*//;s/\s*$//')
    debug "Extracted host-name value: '$VALUE'"

    # Copy the appropriate configuration based on the value
    if [[ "$VALUE" == "t250" ]]; then
        info "host-name is t250. Copying t250.cfg to printer.cfg..."
        cp "$CONFIG_DIR/t250.cfg" "$PRINTER_CFG"
    elif [[ "$VALUE" == "t100" ]]; then
        info "host-name is t100. Copying t100.cfg to printer.cfg..."
        cp "$CONFIG_DIR/t100.cfg" "$PRINTER_CFG"
    else
        error "Unknown value for host-name: '$VALUE'. No action performed."
        exit 1
    fi

    # Adjust ownership and permissions for pi user
    chown "$(current_user):$(current_user)" "$PRINTER_CFG"
    chmod 644 "$PRINTER_CFG"
    info "Ownership set to user '$(current_user)' and permissions set to 644 for $PRINTER_CFG."

else
    error "Avahi configuration file not found: $AVAHI_PATH"
    exit 1
fi
