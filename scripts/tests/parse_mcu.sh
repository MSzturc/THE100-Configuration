#!/bin/bash

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
HELPERS_DIR="$SCRIPT_DIR/../helpers"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

source "$HELPERS_DIR/parse_mcu.sh"

# Tiny assertion helpers
TESTS_RUN=0
TESTS_FAILED=0

assert_equals() {
    local expected=$1
    local actual=$2
    local label=$3
    TESTS_RUN=$((TESTS_RUN + 1))
    if [ "$expected" = "$actual" ]; then
        echo "  ok  - $label"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo "  FAIL - $label"
        echo "         expected: '$expected'"
        echo "         actual:   '$actual'"
    fi
}

assert_nonzero_exit() {
    local actual_exit=$1
    local label=$2
    TESTS_RUN=$((TESTS_RUN + 1))
    if [ "$actual_exit" -ne 0 ]; then
        echo "  ok  - $label"
    else
        TESTS_FAILED=$((TESTS_FAILED + 1))
        echo "  FAIL - $label (expected non-zero exit, got 0)"
    fi
}

# Build a temp fixture tree and return its path
make_tmp() {
    local tmp
    tmp=$(mktemp -d)
    echo "$tmp"
}

# --- Tests ---

test_mcu_in_root_file() {
    echo "test_mcu_in_root_file:"
    local tmp; tmp=$(make_tmp)
    cat > "$tmp/printer.cfg" <<'EOF'
[mcu]
serial: /dev/foo
cpu: stm32h723xx

[printer]
kinematics: cartesian
EOF
    local out; out=$(find_mcu_in_config "$tmp/printer.cfg")
    assert_equals "serial=/dev/foo" "$(echo "$out" | grep '^serial=')" "serial extracted"
    assert_equals "cpu=stm32h723xx" "$(echo "$out" | grep '^cpu=')" "cpu extracted"
    rm -rf "$tmp"
}

test_mcu_in_included_file() {
    echo "test_mcu_in_included_file:"
    local tmp; tmp=$(make_tmp)
    mkdir -p "$tmp/boards/kraken"
    cat > "$tmp/boards/kraken/config.cfg" <<'EOF'
[mcu]
serial: /dev/btt-kraken
cpu: stm32h723xx
EOF
    cat > "$tmp/printer.cfg" <<'EOF'
[include boards/kraken/config.cfg]

[printer]
kinematics: cartesian
EOF
    local out; out=$(find_mcu_in_config "$tmp/printer.cfg")
    assert_equals "serial=/dev/btt-kraken" "$(echo "$out" | grep '^serial=')" "serial from included file"
    assert_equals "cpu=stm32h723xx" "$(echo "$out" | grep '^cpu=')" "cpu from included file"
    rm -rf "$tmp"
}

test_include_path_relative_to_including_file() {
    echo "test_include_path_relative_to_including_file:"
    local tmp; tmp=$(make_tmp)
    mkdir -p "$tmp/sub/boards"
    cat > "$tmp/sub/boards/board.cfg" <<'EOF'
[mcu]
serial: /dev/relative
cpu: stm32f446xx
EOF
    cat > "$tmp/sub/intermediate.cfg" <<'EOF'
[include boards/board.cfg]
EOF
    cat > "$tmp/printer.cfg" <<'EOF'
[include sub/intermediate.cfg]
EOF
    local out; out=$(find_mcu_in_config "$tmp/printer.cfg")
    assert_equals "serial=/dev/relative" "$(echo "$out" | grep '^serial=')" "nested include resolved relative to includer"
    assert_equals "cpu=stm32f446xx" "$(echo "$out" | grep '^cpu=')" "cpu from nested include"
    rm -rf "$tmp"
}

test_include_with_parent_dir() {
    echo "test_include_with_parent_dir:"
    local tmp; tmp=$(make_tmp)
    mkdir -p "$tmp/a"
    mkdir -p "$tmp/b"
    cat > "$tmp/b/board.cfg" <<'EOF'
[mcu]
serial: /dev/parent
cpu: rp2040
EOF
    cat > "$tmp/a/printer.cfg" <<'EOF'
[include ../b/board.cfg]
EOF
    local out; out=$(find_mcu_in_config "$tmp/a/printer.cfg")
    assert_equals "serial=/dev/parent" "$(echo "$out" | grep '^serial=')" "../ include resolved"
    assert_equals "cpu=rp2040" "$(echo "$out" | grep '^cpu=')" "../ include cpu"
    rm -rf "$tmp"
}

test_ignores_commented_mcu() {
    echo "test_ignores_commented_mcu:"
    local tmp; tmp=$(make_tmp)
    cat > "$tmp/printer.cfg" <<'EOF'
#[mcu]
#serial: /dev/wrong
#cpu: wrongcpu

[mcu]
serial: /dev/right
cpu: stm32h723xx
EOF
    local out; out=$(find_mcu_in_config "$tmp/printer.cfg")
    assert_equals "serial=/dev/right" "$(echo "$out" | grep '^serial=')" "commented mcu ignored"
    assert_equals "cpu=stm32h723xx" "$(echo "$out" | grep '^cpu=')" "commented cpu ignored"
    rm -rf "$tmp"
}

test_ignores_commented_include() {
    echo "test_ignores_commented_include:"
    local tmp; tmp=$(make_tmp)
    cat > "$tmp/decoy.cfg" <<'EOF'
[mcu]
serial: /dev/decoy
cpu: decoycpu
EOF
    mkdir -p "$tmp/real"
    cat > "$tmp/real/board.cfg" <<'EOF'
[mcu]
serial: /dev/real
cpu: realcpu
EOF
    cat > "$tmp/printer.cfg" <<'EOF'
#[include decoy.cfg]
[include real/board.cfg]
EOF
    local out; out=$(find_mcu_in_config "$tmp/printer.cfg")
    assert_equals "serial=/dev/real" "$(echo "$out" | grep '^serial=')" "commented include ignored"
    rm -rf "$tmp"
}

test_missing_mcu_returns_error() {
    echo "test_missing_mcu_returns_error:"
    local tmp; tmp=$(make_tmp)
    cat > "$tmp/printer.cfg" <<'EOF'
[printer]
kinematics: cartesian
EOF
    find_mcu_in_config "$tmp/printer.cfg" >/dev/null 2>&1
    local rc=$?
    assert_nonzero_exit "$rc" "missing mcu yields non-zero exit"
    rm -rf "$tmp"
}

test_missing_include_target_continues() {
    echo "test_missing_include_target_continues:"
    local tmp; tmp=$(make_tmp)
    cat > "$tmp/printer.cfg" <<'EOF'
[include nope/does_not_exist.cfg]

[mcu]
serial: /dev/still_works
cpu: stm32h723xx
EOF
    local out; out=$(find_mcu_in_config "$tmp/printer.cfg")
    assert_equals "serial=/dev/still_works" "$(echo "$out" | grep '^serial=')" "missing include does not abort"
    rm -rf "$tmp"
}

test_conditional_include_prefix() {
    echo "test_conditional_include_prefix:"
    # THE100's enhanced parser supports '[include if:${...} path]'.
    # We don't evaluate the condition; we just need to find [mcu] in any
    # included file. So we treat the conditional include as a normal one.
    local tmp; tmp=$(make_tmp)
    mkdir -p "$tmp/printers"
    cat > "$tmp/printers/t250.cfg" <<'EOF'
[mcu]
serial: /dev/conditional
cpu: stm32h723xx
EOF
    cat > "$tmp/printer.cfg" <<'EOF'
[include if:${constants.printer == 't250'} printers/t250.cfg]
EOF
    local out; out=$(find_mcu_in_config "$tmp/printer.cfg")
    assert_equals "serial=/dev/conditional" "$(echo "$out" | grep '^serial=')" "conditional include followed"
    assert_equals "cpu=stm32h723xx" "$(echo "$out" | grep '^cpu=')" "conditional include cpu"
    rm -rf "$tmp"
}

test_real_repo_printer_cfg() {
    echo "test_real_repo_printer_cfg:"
    # The user's printer.cfg uses relative includes like
    # '../../mainsail.cfg' and '../boards/btt-kraken/config.cfg', which
    # imply the file lives at <root>/<level1>/<level2>/printer.cfg with
    # mainsail.cfg at <root>/ and boards/ at <root>/<level1>/.
    local tmp; tmp=$(make_tmp)
    mkdir -p "$tmp/printer_data/config"
    cp "$REPO_ROOT/printer.cfg" "$tmp/printer_data/config/printer.cfg"
    # 'boards/' must be a sibling of 'config/' for '../boards/...' to resolve.
    ln -s "$REPO_ROOT/config/boards" "$tmp/printer_data/boards"
    # mainsail.cfg is referenced as ../../mainsail.cfg; stub it.
    : > "$tmp/mainsail.cfg"

    local out; out=$(find_mcu_in_config "$tmp/printer_data/config/printer.cfg")
    assert_equals "serial=/dev/btt-kraken" "$(echo "$out" | grep '^serial=')" "real printer.cfg serial"
    assert_equals "cpu=stm32h723xx" "$(echo "$out" | grep '^cpu=')" "real printer.cfg cpu"

    rm -rf "$tmp"
}

test_parse_mcu() {
    echo "Starting parse_mcu tests..."
    test_mcu_in_root_file
    test_mcu_in_included_file
    test_include_path_relative_to_including_file
    test_include_with_parent_dir
    test_ignores_commented_mcu
    test_ignores_commented_include
    test_missing_mcu_returns_error
    test_missing_include_target_continues
    test_conditional_include_prefix
    test_real_repo_printer_cfg
    echo
    echo "parse_mcu tests: $((TESTS_RUN - TESTS_FAILED))/$TESTS_RUN passed"
    if [ "$TESTS_FAILED" -gt 0 ]; then
        return 1
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    test_parse_mcu
fi
