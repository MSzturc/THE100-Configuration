# This function retrieves the home directory of the current user.
# - If the script is run with sudo, it determines the home directory of the original user (SUDO_USER).
# - If the script is not run with sudo, it uses the home directory of the current user ($HOME).
user_dir()
{
    # If the script is run with sudo, use the $SUDO_USER variable to determine the original user
    if [[ -n "$SUDO_USER" ]]; then
        # Use the original user's home directory
        local home_dir=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    else
        # Use the home directory of the current user
        local home_dir="$HOME"
    fi

    # Print the home directory
    echo "$home_dir"
}
