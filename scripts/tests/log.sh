#!/bin/bash

# Include the logging functions
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
source "$SCRIPT_DIR/../helpers/log.sh"

# Function to test all log variations
test_logs() {
    echo "Starting log function tests..."

    # Test each log level
    debug "This is a debug message. Useful for developers."
    info "This is an info message. General information for the user."
    warning "This is a warning message. Something may require attention."
    error "This is an error message. Something went wrong."
    check "This is a check message. Everything is OK."

    # Simulate logs within the same second
    debug "Another debug message in the same second."
    info "Another info message in the same second."

    # Simulate a delay to change the timestamp
    sleep 1
    warning "A new log after a timestamp change."

    echo "Log function tests completed."
}

# Run the log tests only if the script is executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    test_logs
fi
