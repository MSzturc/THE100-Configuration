#!/bin/bash

# Where this Script is located
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR"/utils.sh

# Where the user Klipper config is located
KLIPPER_CONFIG_PATH="$(user_dir)/printer_data/config"

# Where to clone THE100-Configuration repository
THE100_CONFIG_PATH="$(user_dir)/THE100-Configuration"

update_configuration() {
    info "Installation of THE100 Configuration..."
    
    # Symlink THE100 Configuration (read-only git repository) to the user's config directory
    info "Creating symbolic links for configuration directories..."
    for dir in config macros scripts; do
        debug "Linking directory: $dir"
        ln -fsn ${THE100_CONFIG_PATH}/$dir ${KLIPPER_CONFIG_PATH}/$dir
    done
    info "Installation of THE100 Configuration completed successfully!"
}

preflight_checks() {
    ensure_root
    is_klipper_installed
    is_configuration_installed
}

preflight_checks
update_configuration