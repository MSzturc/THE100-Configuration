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

# Where the BD_Sensor folder is located
BD_SENSOR_PATH="$(user_dir)/Bed_Distance_sensor/klipper"

# Where the Shake&Tune folder is located
SHAKETUNE_PATH="$(user_dir)/klippain_shaketune"

# This function sets up git hooks for THE100-Configuration, Klipper, and Moonraker.
# The post-merge hooks ensure that specific scripts are executed automatically
# after a 'git pull' or 'git merge' operation in each repository. We use it to reapply
# install scripts for different Klipper addons.
install_hooks()
{
    info "Installing git hooks..."

    # Check if the post-merge hook for THE100-Configuration does not already exist as a symbolic link
    if [[ ! -L "$THE100_CONFIG_PATH/.git/hooks/post-merge" ]]
    then
        # Create a symbolic link for the THE100-Configuration post-merge script
        ln -s "$SCRIPT_DIR/post-merge-configuration.sh" "$THE100_CONFIG_PATH/.git/hooks/post-merge"
        info "Post-merge hook set up for THE100-Configuration."
    fi

    # Check if the post-merge hook for klipper does not already exist as a symbolic link
    if [[ ! -L "$KLIPPER_PATH/.git/hooks/post-merge" ]]
    then
        # Create a symbolic link for klipper post-merge script
        ln -s "$SCRIPT_DIR/post-merge-klipper.sh" "$KLIPPER_PATH/.git/hooks/post-merge"
        info "Post-merge hook set up for klipper."
    fi

    # Check if the post-merge hook for moonraker does not already exist as a symbolic link
    if [[ ! -L "$MOONRAKER_PATH/.git/hooks/post-merge" ]]
    then
        # Create a symbolic link for moonraker post-merge script
        ln -s "$SCRIPT_DIR/post-merge-moonraker.sh" "$MOONRAKER_PATH/.git/hooks/post-merge"
        info "Post-merge hook set up for moonraker."
    fi
}
install_shaketune_extension(){
    info "Installing Shake&Tune extension to klipper..."

    # Debug-Ausgabe: Pfade anzeigen
    debug "SHAKETUNE_PATH is set to '$SHAKETUNE_PATH'"
    debug "KLIPPER_PATH is set to '$KLIPPER_PATH'"

    # Check if shaketune directory does not already exist as a symbolic link
    if [[ ! -d "$KLIPPER_PATH/klippy/extras/shaketune" ]]
    then
        debug "Creating symbolic link for shaketune..."
        # Create a symbolic link for shaketune directory
        ln -frsn "$SHAKETUNE_PATH/shaketune" "${KLIPPER_PATH}/klippy/extras/shaketune"
        debug "Symbolic link for shaketune directory created."
    else
        debug "Symbolic link for shaketune directory already exists. Skipping."
    fi

    info "Shake&Tune extension installation completed."
}

preflight_checks() {
    ensure_root
    is_klipper_installed
    is_moonraker_installed
    is_configuration_installed
}

preflight_checks
install_hooks
install_shaketune_extension
restart_klipper_service