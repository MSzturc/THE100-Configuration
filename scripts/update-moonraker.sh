#!/bin/bash

# Where this Script is located
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
source "$SCRIPT_DIR"/utils.sh

preflight_checks() {
    ensure_root
    is_klipper_installed
    is_moonraker_installed
}

preflight_checks
ensure_moonraker_permissions