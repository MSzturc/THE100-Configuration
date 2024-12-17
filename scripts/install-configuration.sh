#!/bin/bash

# Where this Script is located
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR"/utils.sh

# Where the Klipper folder is located
KLIPPER_PATH="$(user_dir)/klipper"

# Where the user Klipper config is located
KLIPPER_CONFIG_PATH="$(user_dir)/printer_data/config"

# Where to clone THE100-Configuration repository
THE100_CONFIG_PATH="$(user_dir)/THE100-Configuration"

# Where the Moonraker folder is located
MOONRAKER_PATH="$(user_dir)/moonraker"

# Branch from MSzturc/THE100-Configuration repo to use during install (default: main)
THE100_CONFIG_REPOSITORY="https://github.com/MSzturc/THE100-Configuration.git"

# Branch from MSzturc/THE100-Configuration repo to use during install (default: main)
THE100_CONFIG_BRANCH="main"

download_configuration() {
    
    if [ -d "$THE100_CONFIG_PATH" ]; then
        info "Configuration repository already found locally at $THE100_CONFIG_PATH. Skipping download."
    else
        info "Configuration repository does not exist at $THE100_CONFIG_PATH. Cloning repository..."
        if git clone --quiet --branch "$THE100_CONFIG_BRANCH" "$THE100_CONFIG_REPOSITORY" "$THE100_CONFIG_PATH"; then
            check "Successfully cloned configuration repository to $THE100_CONFIG_PATH."
        else
            error "Failed to clone configuration repository."
            exit 1
        fi
    fi
}

# This function checks if a 'logs' directory exists in the user's home directory.
# If it doesn't exist, the function creates the directory and sets its permissions to allow 
# read and write access for all users. Additionally, it creates an empty 'theos.log' file 
# in the directory with the same permissions.
install_logs() {

    # Path to the logs directory
    local logs_dir="$(user_dir)/logs"
    local log_file="$logs_dir/theos.log"

    # Check if the 'logs' folder exists
    if [ ! -d "$logs_dir" ]; then
        info "Creating folder: $logs_dir"
        mkdir "$logs_dir"
    else
        debug "Folder already exists: $logs_dir"
    fi

    # Set permissions: read and write for all users (folder and future files)
    chmod 777 "$logs_dir"
    info "Permissions for folder $logs_dir set: read and write for all users."

    # Check if the file 'theos.log' exists, otherwise create it
    if [ ! -f "$log_file" ]; then
        debug "Creating file: $log_file"
        touch "$log_file"
    else
        debug "File already exists: $log_file"
    fi

    # Set permissions: read and write for all users for the file
    chmod 666 "$log_file"
    info "Permissions for file $log_file set: read and write for all users."
}

preflight_checks() {
    ensure_not_root
    is_klipper_installed
}

preflight_checks
download_configuration
install_logs

sudo "$SCRIPT_DIR"/update-configuration.sh
sudo "$SCRIPT_DIR"/update-klipper.sh
sudo "$SCRIPT_DIR"/update-moonraker.sh
sudo "$SCRIPT_DIR"/install-printer-cfg.sh

restart_klipper_service