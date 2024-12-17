# Function to determine the current user running the script.
# If the script is run as root:
#   - It checks the SUDO_USER environment variable to identify the original user.
#   - If SUDO_USER is root, it overrides it with "pi."
#   - If SUDO_USER is not set, it assumes the user is "root."
# If the script is not run as root:
#   - It echoes the value of the USER environment variable, which represents the current logged-in user.
current_user() {
    if [ "$EUID" -eq 0 ]; then
        # If BASE_USER is set, use it
        if [ -n "$BASE_USER" ]; then
            echo "$BASE_USER"
        # Otherwise, check for SUDO_USER
        elif [ -n "$SUDO_USER" ]; then
            if [ "$SUDO_USER" == "root" ]; then
                echo "pi"
            else
                echo "$SUDO_USER"
            fi
        else
            echo "root"
        fi
    else
        # If not root, just return the current user
        echo "$USER"
    fi
}
