#!/bin/bash

# Where this Script is located
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR"/utils.sh

# Where the user Klipper config is located
PRINTER_DATA_PATH="$(user_dir)/printer_data"

# Where the user Klipper config is located
KLIPPER_CONFIG_PATH="${PRINTER_DATA_PATH}/config"

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

update_sudo_permissions() {
    info "Starting sudo permissions setup."

    # Check if the sudoers configuration file for "theos-githooks" already exists
    if [[ -e /etc/sudoers.d/030-theos-githooks ]]
    then
        debug "Found existing sudoers file: /etc/sudoers.d/030-theos-githooks. Removing it."
        rm /etc/sudoers.d/030-theos-githooks
    else
        debug "No existing sudoers file found. Proceeding with setup."
    fi

    # Create a temporary file for the new sudoers configuration
    info "Creating temporary sudoers file at /tmp/030-theos-githooks."
    touch /tmp/030-theos-githooks

    # Write the new sudoers rules into the temporary file
    info "Writing new sudo rules to temporary file."
    cat > /tmp/030-theos-githooks << EOF
$(current_user) ALL=(ALL) NOPASSWD: $(user_dir)/THE100-Configuration/scripts/update-configuration.sh
$(current_user) ALL=(ALL) NOPASSWD: $(user_dir)/THE100-Configuration/scripts/update-klipper.sh
$(current_user) ALL=(ALL) NOPASSWD: $(user_dir)/THE100-Configuration/scripts/update-moonraker.sh
EOF

    # Set ownership of the temporary file to root
    debug "Changing ownership of /tmp/030-theos-githooks to root:root."
    chown root:root /tmp/030-theos-githooks

    # Set permissions to read-only for the owner
    debug "Setting file permissions to 440 (read-only for root) on /tmp/030-theos-githooks."
    chmod 440 /tmp/030-theos-githooks

    # Copy the temporary file to the sudoers directory
    info "Copying temporary file to /etc/sudoers.d/030-theos-githooks with preserved permissions."
    cp --preserve=mode /tmp/030-theos-githooks /etc/sudoers.d/030-theos-githooks

    # Clean up: remove the temporary file
    debug "Removing temporary file: /tmp/030-theos-githooks."
    rm /tmp/030-theos-githooks

    info "Sudo permissions setup completed successfully."
}

preflight_checks() {
    ensure_root
    is_klipper_installed
    is_configuration_installed
}

preflight_checks
update_configuration
update_udev_rules
update_sudo_permissions
ensure_moonraker_permissions