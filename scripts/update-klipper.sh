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

preflight_checks() {
    ensure_root
    is_klipper_installed
}

preflight_checks
install_hooks