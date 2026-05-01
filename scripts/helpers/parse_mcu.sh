#!/bin/bash

# parse_mcu.sh — locate the primary [mcu] section across a Klipper-style
# printer.cfg tree, following [include ...] directives the same way the
# Klipper config parser does (paths resolved relative to the file that
# contains the include).
#
# Usage:
#   source helpers/parse_mcu.sh
#   find_mcu_in_config /path/to/printer.cfg
#
# On success prints two lines on stdout:
#   serial=<value>
#   cpu=<value>
# and exits 0. On failure (file missing or no [mcu] block with serial+cpu
# found) exits non-zero with no output.

# Flatten a Klipper config file by inlining (non-commented) [include ...]
# directives recursively. Missing include targets are silently skipped so
# that an unresolvable include never aborts the search for [mcu].
_parse_mcu_flatten() {
    local file=$1
    local abs
    abs=$(realpath "$file" 2>/dev/null) || return 0
    [ -z "$abs" ] && return 0
    [ -f "$abs" ] || return 0

    if [ -n "${_PARSE_MCU_VISITED[$abs]:-}" ]; then
        return 0
    fi
    _PARSE_MCU_VISITED[$abs]=1

    local dir
    dir=$(dirname "$abs")

    local line stripped inc target
    while IFS= read -r line || [ -n "$line" ]; do
        stripped="${line#"${line%%[![:space:]]*}"}"
        # Pass comments/blank lines through; never treat them as includes
        if [ -z "$stripped" ] || [ "${stripped:0:1}" = "#" ]; then
            printf '%s\n' "$line"
            continue
        fi
        if [[ "$stripped" =~ ^\[include[[:space:]]+([^]]+)\] ]]; then
            inc="${BASH_REMATCH[1]}"
            # Strip THE100 conditional prefix '[include if:${...} path]'
            inc=$(printf '%s' "$inc" | sed -E 's/^if:\$\{[^}]+\}[[:space:]]+//')
            # Trim surrounding whitespace
            inc="${inc#"${inc%%[![:space:]]*}"}"
            inc="${inc%"${inc##*[![:space:]]}"}"
            if [[ "$inc" = /* ]]; then
                target="$inc"
            else
                target="$dir/$inc"
            fi
            _parse_mcu_flatten "$target"
        else
            printf '%s\n' "$line"
        fi
    done < "$abs"
}

# Public entry point
find_mcu_in_config() {
    local file=$1
    [ -f "$file" ] || return 1

    declare -gA _PARSE_MCU_VISITED=()

    local flat serial cpu
    flat=$(_parse_mcu_flatten "$file")

    serial=$(printf '%s\n' "$flat" | awk '
        /^[[:space:]]*\[mcu\][[:space:]]*$/ { flag=1; next }
        /^[[:space:]]*\[/                  { flag=0 }
        flag && /^[[:space:]]*serial:/ {
            sub(/^[[:space:]]*serial:[[:space:]]*/, "")
            sub(/[[:space:]]*#.*$/, "")
            sub(/[[:space:]]+$/, "")
            print
            exit
        }')

    cpu=$(printf '%s\n' "$flat" | awk '
        /^[[:space:]]*\[mcu\][[:space:]]*$/ { flag=1; next }
        /^[[:space:]]*\[/                  { flag=0 }
        flag && /^[[:space:]]*cpu:/ {
            sub(/^[[:space:]]*cpu:[[:space:]]*/, "")
            sub(/[[:space:]]*#.*$/, "")
            sub(/[[:space:]]+$/, "")
            print
            exit
        }')

    if [ -z "$serial" ] || [ -z "$cpu" ]; then
        return 1
    fi

    printf 'serial=%s\n' "$serial"
    printf 'cpu=%s\n' "$cpu"
    return 0
}
