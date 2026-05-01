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


# Call Tests
test_logs
test_parse_mcu
test_z_tilt_points
test_dynamic_mesh
test_twist_compensation
test_dual_wiring
test_nozzle_diameter
test_filament_diameter
test_primeline
test_print_pipeline
test_microsteps
test_tmc_interpolate
test_second_homing_speed
test_safe_z_home
