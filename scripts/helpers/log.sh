#!/bin/bash

# Global variable to store the last used timestamp
LAST_TIMESTAMP=""

# Logging function with precise alignment of log levels
log() {
    local level="$1"
    local color="$2"
    local text="$3"
    local timestamp
    timestamp=$(date +"%Y-%m-%d %H:%M:%S")

    # Fixed width for the timestamp and log level
    local timestamp_width=21
    local level_width=10

    # Check if the timestamp has changed
    if [ "$timestamp" != "$LAST_TIMESTAMP" ]; then
        # Print timestamp and log level
        printf "%-${timestamp_width}s %b%-${level_width}s\e[0m %s\n" "[$timestamp]" "$color" "[$level]" "$text"
        LAST_TIMESTAMP="$timestamp"
    else
        # Print only spaces for the timestamp and align log level
        printf "%-${timestamp_width}s %b%-${level_width}s\e[0m %s\n" " " "$color" "[$level]" "$text"
    fi
}

# Individual functions for each log level
debug() {
    log "DEBUG" "\e[36m" "$1"  # Cyan
}

info() {
    log "INFO" "\e[32m" "$1"  # Green
}

warning() {
    log "WARNING" "\e[33m" "$1"  # Yellow
}

error() {
    log "ERROR" "\e[31m" "$1"  # Red
}

check() {
    log "CHECK" "\e[32m" "$1"  # Green (same as INFO, but for checks)
}
