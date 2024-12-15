#!/bin/bash

source utils.sh

# Where the Klipper folder is located
KLIPPER_PATH="${HOME}/klipper"

# Where the user Klipper config is located
KLIPPER_CONFIG_PATH="${HOME}/printer_data/config"

# Where to clone THE100-Configruation repository
THE100_CONFIG_PATH="${HOME}/THE100-Configruation"

# Branch from MSzturc/THE100-Configruation repo to use during install (default: main)
THE100_CONFIG_REPOSITORY="https://github.com/MSzturc/THE100-Configruation.git"

# Branch from MSzturc/THE100-Configruation repo to use during install (default: main)
THE100_CONFIG_BRANCH="main"

downloadConfiguration() {
    
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

installConfiguration() {
    info "Installation of THE100 Configuration..."
    
    # Symlink THE100 Configuration (read-only git repository) to the user's config directory
    info "Creating symbolic links for configuration directories..."
    for dir in config macros scripts; do
        info "Linking directory: $dir"
        ln -fsn ${THE100_CONFIG_PATH}/$dir ${KLIPPER_CONFIG_PATH}/$dir
    done

    # CHMOD the scripts to be sure they are all executables (Git should keep the modes on files but it's to be sure)
    info "Ensuring scripts are executable..."
    chmod +x ${THE100_CONFIG_PATH}/scripts/install-configuration.sh

    info "Installation of THE100 Configuration completed successfully!"
}


preflight_checks() {
    ensure_not_root
    is_klipper_installed
}

preflight_checks
downloadConfiguration
installConfiguration