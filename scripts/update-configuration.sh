#!/bin/bash

# Where this Script is located
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR"/utils.sh

# Where the user Klipper config is located
KLIPPER_CONFIG_PATH="$(user_dir)/printer_data/config"

# Where to clone THE100-Configuration repository
THE100_CONFIG_PATH="$(user_dir)/THE100-Configuration"

# Where the THEOS Logs are located
THEOS_LOGS_PATH="$(user_dir)/logs"

update_configuration() {
    info "Installation of THE100 Configuration..."
    
    # Symlink THE100 Configuration (read-only git repository) to the user's config directory
    info "Creating symbolic links for configuration directories..."
    for dir in config macros scripts; do
        debug "Linking directory: $dir"
        ln -fsn ${THE100_CONFIG_PATH}/$dir ${KLIPPER_CONFIG_PATH}/$dir
    done

    info "Creating symbolic links for logs directory..."
    ln -fsn ${THEOS_LOGS_PATH} ${KLIPPER_CONFIG_PATH}/logs

    info "Installation of THE100 Configuration completed successfully!"
}

update_udev_rules()
{
  info "Updating THEOS Board device symlinks.."
  
  # Remove existing udev rules files in /etc/udev/rules.d/ 
  # All board-specific udev rule files in THE100-Configuration are prefixed with '98-'
  rm -f /etc/udev/rules.d/98-*.rules
  
  # Create symbolic links for the updated udev rules from the configuration directory
  # Source: THE100-Configuration/config/boards/*/*.rules
  # Destination: /etc/udev/rules.d/ (udev directory where rule files are loaded)
  # This ensures the system uses the latest board-specific udev rules for device management
  ln -s $(user_dir)/THE100-Configuration/config/boards/*/*.rules /etc/udev/rules.d/
}

preflight_checks() {
    ensure_root
    is_klipper_installed
    is_configuration_installed
}

preflight_checks
update_configuration
update_udev_rules