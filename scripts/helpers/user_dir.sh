# This function retrieves the home directory of the current user.
# - If the script is run with sudo, it determines the home directory of the original user (SUDO_USER).
# - If the script is not run with sudo, it uses the home directory of the current user ($HOME).
user_dir()
{
    local home_dir

    # Check if BASE_USER environment variable is set
    if [[ -n "$BASE_USER" ]]; then
        echo "BASE_USER ist gesetzt auf '$BASE_USER'."
        home_dir=$(getent passwd "$BASE_USER" | cut -d: -f6)
        echo "Home-Verzeichnis für BASE_USER: $home_dir"
    elif [[ -n "$SUDO_USER" ]]; then
        echo "SUDO_USER ist gesetzt auf '$SUDO_USER'."
        home_dir=$(getent passwd "$SUDO_USER" | cut -d: -f6)
        echo "Home-Verzeichnis für SUDO_USER: $home_dir"
    else
        echo "Weder BASE_USER noch SUDO_USER sind gesetzt. Verwende aktuelles HOME: $HOME"
        home_dir="$HOME"
    fi

    # Print the final home directory
    echo "Verwendetes Home-Verzeichnis: $home_dir"
    echo "$home_dir"
}