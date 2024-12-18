# Determines the current user based on the context in which the script is executed.
# - If the script is run with sudo:
#   - It checks if BASE_USER is set and uses it if available.
#   - Otherwise, it evaluates the SUDO_USER environment variable:
#     - If SUDO_USER is 'root', it defaults to 'pi' to address specific use cases
#       (e.g., CustomPIOS image-building processes starting as root).
#     - Otherwise, it returns the value of SUDO_USER.
# - If the script is run as root:
#   - Neither BASE_USER nor SUDO_USER is set, it defaults to 'root.'
# - If the script is not run as root, it returns the current logged-in user ($USER).
current_user() {
    if [ "$EUID" -eq 0 ]; then
        # If BASE_USER is set, use it
        if [ -n "$BASE_USER" ]; then
            echo "$BASE_USER"
        # Otherwise, check the SUDO_USER variable
        elif [ -n "$SUDO_USER" ]; then
            # Handle specific case where SUDO_USER is 'root'
            if [ "$SUDO_USER" == "root" ]; then
                echo "pi"
            else
                echo "$SUDO_USER"
            fi
        else
            echo "root"
        fi
    else
        # If not run as root, return the current logged-in user
        echo "$USER"
    fi
}
