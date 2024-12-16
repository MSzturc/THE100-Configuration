#!/bin/bash

# Where this Script is located
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR"/utils.sh

preflight_checks() {
    ensure_root
    is_klipper_installed
}

hallo()
{
    local log_file="$(user_dir)/printer_data/config/info.log"
    echo "Hallo" > "$log_file"
}

preflight_checks
hallo