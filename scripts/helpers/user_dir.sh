# This function retrieves the home directory of the current user.
# - If the script is executed with sudo and SUDO_USER is set to 'root',
#   it overrides SUDO_USER with 'pi' to avoid issues.
# - If the BASE_USER environment variable is set, the home directory
#   is determined based on BASE_USER.
# - Otherwise, it falls back to the home directory of the current user ($HOME).
user_dir()
{
    local home_dir

    # CustomPIOS starts the image-building process as 'root',
    # which causes SUDO_USER to also be 'root', creating a potential issue.
    # As a workaround, we set SUDO_USER to 'pi' if it's 'root'.
    # This is not a concern since the final step of the image-building
    # process disables the root user, meaning this case won't occur
    # during normal usage.
    if [[ "$SUDO_USER" == "root" ]]; then
        SUDO_USER="pi"
    fi

    # Check if the BASE_USER environment variable is set
    if [[ -n "$BASE_USER" ]]; then
        home_dir=$(getent passwd "$BASE_USER" | cut -d: -f6)
    elif [[ -n "$SUDO_USER" ]]; then
        home_dir=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    else
        home_dir="$HOME"
    fi

    echo "$home_dir"
}