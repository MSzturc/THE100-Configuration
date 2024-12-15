#!/bin/bash

TEST_DIR="./tests"

if [[ -d "$TEST_DIR" ]]; then
    for tests in "$TEST_DIR"/*.sh; do
        if [[ -f "$tests" ]]; then
            source "$tests"
        fi
    done
else
    echo "Verzeichnis $TEST_DIR existiert nicht."
    exit 1
fi


# Call Test
test_logs
