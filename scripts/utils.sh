#!/bin/bash

# Where this Script is located
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Include the logging functions
source "$SCRIPT_DIR"/helpers/log.sh

# Function to ensure the script is NOT run as root.
ensure_not_root() {
    if [ "$EUID" -eq 0 ]; then
        error "This script must not be run as root!"
        exit 1
    else
        check "Script is not being run as root. Proceeding..."
    fi
}

# Function to ensure the script IS run as root.
ensure_root() {
    if [ "$EUID" -ne 0 ]; then
        error "This script must be run as root!"
        exit 1
    else
        check "Script is being run as root. Proceeding..."
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

# This function retrieves the home directory of the current user.
# - If the script is run with sudo, it determines the home directory of the original user (SUDO_USER).
# - If the script is not run with sudo, it uses the home directory of the current user ($HOME).
user_dir()
{
    # If the script is run with sudo, use the $SUDO_USER variable to determine the original user
    if [[ -n "$SUDO_USER" ]]; then
        # Use the original user's home directory
        local home_dir=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    else
        # Use the home directory of the current user
        local home_dir="$HOME"
    fi

    # Print the home directory
    echo "$home_dir"
}
