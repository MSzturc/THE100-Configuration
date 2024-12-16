#!/bin/bash

# Global variable to store the last used timestamp
LAST_FILE_TIMESTAMP=""
LAST_CONSOLE_TIMESTAMP=""

# Logging function with precise alignment of log levels
log() {
    LOG_FILE="$(user_dir)/logs/theos.log"

    local level="$1"
    local color="$2"
    local text="$3"
    local caller
    local timestamp

    # Determine the caller function/file
    caller=$(caller 1 | awk '{print $2}')

    timestamp=$(date +"%Y-%m-%d %H:%M:%S")

    # Fixed width for the timestamp and fixed width for the log level brackets
    local timestamp_width=22
    local level_width=10

    # Center the log level within the fixed width
    local level_padding=$(( (level_width - ${#level}) / 2 ))
    local padded_level="$(printf "%${level_padding}s%s%${level_padding}s" "" "$level" "")"

    # Append log to the log file with the same format as console output
    mkdir -p "$(user_dir)/logs"
    if [ "$timestamp" != "$LAST_FILE_TIMESTAMP" ]; then
        printf "%-${timestamp_width}s[%-${level_width}s] %s (%s)\n" "[$timestamp]" "$padded_level" "$text" "$caller" >> "$LOG_FILE"
        LAST_FILE_TIMESTAMP="$timestamp"
    else
        printf "%*s[%-${level_width}s] %s (%s)\n" ${timestamp_width} "" "$padded_level" "$text" "$caller" >> "$LOG_FILE"
    fi

    # Print to console only if not DEBUG or debugging is active
    if [ "$level" != "DEBUG" ] || [ -f "$(user_dir)/logs/debugging.active" ]; then
        if [ "$timestamp" != "$LAST_CONSOLE_TIMESTAMP" ]; then
            # Print timestamp and log level
            printf "%-${timestamp_width}s%b[%-${level_width}s]\e[0m %s\n" "[$timestamp]" "$color" "$padded_level" "$text"
            LAST_CONSOLE_TIMESTAMP="$timestamp"
        else
            # Print only spaces for the timestamp and align log level
            printf "%*s%b[%-${level_width}s]\e[0m %s\n" ${timestamp_width} "" "$color" "$padded_level" "$text"
        fi
    fi
}

# Individual functions for each log level
debug() {
    DEBUGGING_FILE="$(user_dir)/logs/debugging.active"
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

# Function to enable debugging
enable_debugging() {
    DEBUGGING_FILE="$(user_dir)/logs/debugging.active"
    mkdir -p "$(user_dir)/logs"
    touch "$DEBUGGING_FILE"
    info "Debugging enabled."
}

# Function to disable debugging
disable_debugging() {
    DEBUGGING_FILE="$(user_dir)/logs/debugging.active"
    if [ -f "$DEBUGGING_FILE" ]; then
        rm "$DEBUGGING_FILE"
        info "Debugging disabled."
    fi
}
