#!/bin/bash

# Where this script is located
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR"/utils.sh

# Paths to the configuration file and printer configuration
AVAHI_PATH="/etc/avahi/avahi-daemon.conf"
PRINTER_CFG="$(user_dir)/printer_data/config/printer.cfg"
CONFIG_DIR="$(user_dir)/printer_data/config/config/templates"

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
    debug=$(grep -E "^\s*host-name\s*=" "$AVAHI_PATH" | sed -E 's/.*=\s*//;s/\s*$//')
    debug "Extracted host-name value: '$VALUE'"

    # Check if VALUE is set
    if [[ -z "$VALUE" ]]; then
        debug "No value provided for 'VALUE'. Fallback to 't250' as default"
        VALUE="t250"
    fi

    # Define the path to the desired configuration file
    CONFIG_FILE="$CONFIG_DIR/${VALUE}.cfg"

    # Check if the configuration file exists
    if [[ -f "$CONFIG_FILE" ]]; then
        info "host-name is '$VALUE'. Copying '$CONFIG_FILE' to '$PRINTER_CFG'..."
        cp "$CONFIG_FILE" "$PRINTER_CFG"
        if [[ $? -ne 0 ]]; then
            error "Error copying '$CONFIG_FILE' to '$PRINTER_CFG'."
            exit 1
        fi
    fi

    # Adjust ownership and permissions for pi user
    chown "$(current_user):$(current_user)" "$PRINTER_CFG"
    chmod 644 "$PRINTER_CFG"
    info "Ownership set to user '$(current_user)' and permissions set to 644 for $PRINTER_CFG."

else
    error "Avahi configuration file not found: $AVAHI_PATH"
    exit 1
fi
