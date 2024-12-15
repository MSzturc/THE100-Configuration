#!/bin/bash

# Include the logging functions
source ./helpers/log.sh

# Function to ensure the script is NOT run as root.
ensure_not_root() {
    if [ "$EUID" -eq 0 ]; then
        error "This script must not be run as root!"
        exit 1
    else
        check "Script is not being run as root. Proceeding..."
    fi
}

# Function to check if Klipper is installed
is_klipper_installed() {
    if [ "$(sudo systemctl list-units --full -all -t service --no-legend | grep -F 'klipper.service')" ]; then
        check "Klipper service found! Proceeding..."
    else
        error "Klipper service not found, please install Klipper first!"
        exit -1
    fi
}

# Function to restart the Klipper service
restart_klipper_service() {
    if sudo systemctl restart klipper; then
        info "Klipper service restarted successfully."
    else
        error "Failed to restart the Klipper service."
        exit 1
    fi
}
