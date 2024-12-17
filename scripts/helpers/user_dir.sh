# This function retrieves the home directory of the current user.
# - If the script is run with sudo, and SUDO_USER=root, it overrides SUDO_USER with 'pi'.
# - If the BASE_USER variable is set, it determines the home directory based on BASE_USER.
# - Otherwise, it uses the home directory of the current user ($HOME).
user_dir()
{
    local home_dir

    # Wenn SUDO_USER=root, setze SUDO_USER=pi
    if [[ "$SUDO_USER" == "root" ]]; then
        SUDO_USER="pi"
    fi

    # Check if BASE_USER environment variable is set
    if [[ -n "$BASE_USER" ]]; then
        home_dir=$(getent passwd "$BASE_USER" | cut -d: -f6)
    elif [[ -n "$SUDO_USER" ]]; then
        home_dir=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    else
        home_dir="$HOME"
    fi

    echo "$home_dir"
}
