#!/bin/bash

# Where this Script is located
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# Include the logging functions
source "$SCRIPT_DIR"/helpers/log.sh
source "$SCRIPT_DIR"/helpers/user_dir.sh
source "$SCRIPT_DIR"/helpers/current_user.sh

# Where to clone THE100-Configuration repository
THE100_CONFIG_PATH="$(user_dir)/THE100-Configuration"

# Where the user Klipper config is located
PRINTER_DATA_PATH="$(user_dir)/printer_data"

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
        exit 1
    fi
}

# Function to check if THE100-Configuration is installed
is_configuration_installed() {
    if [ -d "$THE100_CONFIG_PATH" ]; then
        check "THE100-Configuration folder found. Proceeding..."
    else
        error "Error: THE100-Configuration folder not found at '$THE100_CONFIG_PATH'."
        exit 1
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

ensure_moonraker_permissions() {
    local file_path="${PRINTER_DATA_PATH}/moonraker.asvc"

    info "Authorized Moonraker to manage Services..."

    # List of services that Moonraker should manage
    local elements=(
        "klipper_mcu"          
        "webcamd"                
        "MoonCord"               
        "KlipperScreen"          
        "moonraker-telegram-bot" 
        "sonar"                  
        "crowsnest"               
    )

    # TODO: Define THE100-Configuration as managed service

    # Write the service names to the file, one per line
    {
        for element in "${elements[@]}"; do
            echo "$element"
        done
    } > "$file_path"
    
    # Check if writing to the file was successful
    if [ $? -ne 0 ]; then
        error "Failed to write to file '$file_path'. Ensure the path is correct and writable."
        exit 1
    fi

    # Set file permissions to 644 (readable by all, writable only by the owner)
    chmod 644 "$file_path"
    if [ $? -ne 0 ]; then
        error "Failed to set permissions on '$file_path'."
        exit 1
    fi

    # Set the file owner to user 'pi' and group 'pi'
    chown pi:pi "$file_path"
    if [ $? -ne 0 ]; then
        error "Failed to change ownership of '$file_path'."
        exit 1
    fi

    info "Successfully updated '$file_path'"
}