# This function retrieves the home directory of the current user.
# - If the script is run with sudo, it determines the home directory of the original user (SUDO_USER).
# - If the script is not run with sudo, it uses the home directory of the current user ($HOME).
user_dir()
{
    local home_dir

    # Check if BASE_USER environment variable is set
    if [[ -n "$BASE_USER" ]]; then
        # Use the home directory of the user specified in BASE_USER
        home_dir=$(getent passwd "$BASE_USER" | cut -d: -f6)
    elif [[ -n "$SUDO_USER" ]]; then
        # If the script is run with sudo, use the $SUDO_USER variable
        home_dir=$(getent passwd "$SUDO_USER" | cut -d: -f6)
    else
        # Use the home directory of the current user
        home_dir="$HOME"
    fi

    # Print the home directory
    echo "$home_dir"
}