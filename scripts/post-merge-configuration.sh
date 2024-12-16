#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "$(realpath -- "${BASH_SOURCE[0]}")" )" &> /dev/null && pwd )
sudo "$SCRIPT_DIR"/update-configuration.sh