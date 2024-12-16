# Function to determine the current user running the script.
# If the script is run as root:
#   - It checks the SUDO_USER environment variable to identify the original user.
#   - If SUDO_USER is set, it echoes that user.
#   - If SUDO_USER is not set, it assumes the user is "root."
# If the script is not run as root:
#   - It echoes the value of the USER environment variable, which represents the current logged-in user.
current_user() {
    if [ "$EUID" -eq 0 ]; then
        # If running as root, check for the original user in SUDO_USER
        if [ -n "$SUDO_USER" ]; then
            echo "$SUDO_USER"
        else
            echo "root"
        fi
    else
        echo "$USER"
    fi
}
