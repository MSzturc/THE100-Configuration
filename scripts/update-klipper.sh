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

install_bdsensor_extension(){
    info "Installing BD_Sensor extension to klipper..."
    
    # Debug-Ausgabe: Pfade anzeigen
    debug "BD_SENSOR_PATH is set to '$BD_SENSOR_PATH'"
    debug "KLIPPER_PATH is set to '$KLIPPER_PATH'"

    # Check if BDsensor.py does not already exist as a symbolic link
    if [[ ! -L "$KLIPPER_PATH/klippy/plugins/BDsensor.py" ]]
    then
        debug "Creating symbolic link for BDsensor.py..."
        # Create a symbolic link for BDsensor.py
        ln -s "$BD_SENSOR_PATH/BDsensor.py" "$KLIPPER_PATH/klippy/plugins/BDsensor.py"
        debug "Symbolic link for BDsensor.py created."
    else
        debug "Symbolic link for BDsensor.py already exists. Skipping."
    fi

    # Check if BD_sensor.c does not already exist as a symbolic link
    if [[ ! -L "$KLIPPER_PATH/src/BD_sensor.c" ]]
    then
        debug "Creating symbolic link for BD_sensor.c..."
        # Create a symbolic link for BD_sensor.c
        ln -s "$BD_SENSOR_PATH/BD_sensor.c" "$KLIPPER_PATH/src/BD_sensor.c"
        debug "Symbolic link for BD_sensor.c created."
    else
        debug "Symbolic link for BD_sensor.c already exists. Skipping."
    fi

    # Check if make_with_bdsensor.sh does not already exist as a symbolic link
    if [[ ! -L "$KLIPPER_PATH/make_with_bdsensor.sh" ]]
    then
        debug "Creating symbolic link for make_with_bdsensor.sh..."
        # Create a symbolic link for make_with_bdsensor.sh
        ln -s "$BD_SENSOR_PATH/make_with_bdsensor.sh" "$KLIPPER_PATH/make_with_bdsensor.sh"
        debug "Symbolic link for make_with_bdsensor.sh created."
    else
        debug "Symbolic link for make_with_bdsensor.sh already exists. Skipping."
    fi

    # Adding files to .git/info/exclude to prevent them from being tracked by git
    if ! grep -q "klippy/plugins/BDsensor.py" "$KLIPPER_PATH/.git/info/exclude"; then
        debug "Adding BDsensor.py to .git/info/exclude..."
        echo "klippy/plugins/BDsensor.py" >> "$KLIPPER_PATH/.git/info/exclude"
        debug "BDsensor.py added to .git/info/exclude."
    else
        debug "BDsensor.py already in .git/info/exclude. Skipping."
    fi

    if ! grep -q "src/BD_sensor.c" "$KLIPPER_PATH/.git/info/exclude"; then
        debug "Adding BD_sensor.c to .git/info/exclude..."
        echo "src/BD_sensor.c" >> "$KLIPPER_PATH/.git/info/exclude"
        debug "BD_sensor.c added to .git/info/exclude."
    else
        debug "BD_sensor.c already in .git/info/exclude. Skipping."
    fi

    if ! grep -q "make_with_bdsensor.sh" "$KLIPPER_PATH/.git/info/exclude"; then
        debug "Adding make_with_bdsensor.sh to .git/info/exclude..."
        echo "make_with_bdsensor.sh" >> "$KLIPPER_PATH/.git/info/exclude"
        debug "make_with_bdsensor.sh added to .git/info/exclude."
    else
        debug "make_with_bdsensor.sh already in .git/info/exclude. Skipping."
    fi
    
    info "BD_Sensor extension installation completed."
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
install_bdsensor_extension
install_shaketune_extension