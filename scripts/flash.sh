#!/bin/bash

# Funktion zum Warten auf den MCU-Neustart
wait_for_mcu_reboot() {
    local board=$1
    local timeout=${2:-10} # Standard-Timeout auf 10 Sekunden
    local elapsed=0

    echo "Waiting for MCU Reboot..."
    while [ ! -h "/dev/$board" ] && [ $elapsed -lt $timeout ]; do
        sleep 1
        elapsed=$((elapsed + 1))
    done

    if [ -h "/dev/$board" ]; then
        echo "MCU reboot successful."
        return 0
    else
        echo "Error: MCU did not reboot within $timeout seconds."
        return 1
    fi
}


# Sicherstellen, dass das Skript als root ausgeführt wird
if [ "$EUID" -ne 0 ]; then
    echo "ERROR: Please run as root"
    exit 1
fi

# Aktuelles Verzeichnis des Skripts ermitteln
current_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)

# Pfad zur printer.cfg, die ausgelesen werden soll
printer_cfg="/home/pi/printer_data/config/printer.cfg"

# Prüfen, ob die printer.cfg existiert und lesbar ist
if [ ! -f "$printer_cfg" ]; then
    echo "Error: Configuration file $printer_cfg not found or not readable!"
    exit 1
fi

echo "Searching for MCU..."

# Werte aus dem [mcu]-Abschnitt extrahieren
serial=$(awk '/\[mcu\]/{flag=1; next} /\[/{flag=0} flag && /^[^#]*serial:/ {print $2}' "$printer_cfg")
cpu=$(awk '/\[mcu\]/{flag=1; next} /\[/{flag=0} flag && /^[^#]*cpu:/ {print $2}' "$printer_cfg")

if [ -z "$serial" ] || [ -z "$cpu" ]; then
    echo "Error: Could not extract 'serial' or 'cpu' from the [mcu] section in $printer_cfg!"
    exit 1
fi

# Extrahieren des Boards (letzter Teil der Serial)
board=$(basename "$serial")

# Prüfen, ob ein Konfigurationsordner für das Board existiert
board_dir=$(realpath "$current_dir/../boards/$board")

if [ ! -d "$board_dir" ]; then
    echo "Error: $board not supported!"
    exit 1
fi

# Pfade definieren
source_file="$board_dir/firmware.config"
target_file="/home/pi/klipper/.config"

# Firmware-Konfigurationsdatei in Klipper-Verzeichnis kopieren
if [ -f "$source_file" ]; then
    echo "Copying firmware.config for board $board to $target_file"
    cp "$source_file" "$target_file" || {
        echo "Error: Failed to copy firmware.config for board $board"
        exit 1
    }
else
    echo "Error: Source file $source_file for board $board does not exist!"
    exit 1
fi

# In das Klipper-Verzeichnis wechseln
pushd /home/pi/klipper > /dev/null || exit

# Klipper kompilieren
echo "Building Klipper Firmware..."
make

echo "Looking for MCU: Serial=$serial, CPU=$cpu, Board=$board"

# Prüfen, ob das in der Konfiguration definierte Gerät existiert
if [ -e "$serial" ]; then
    echo "MCU found at $serial"
else
    #Prüfen, ob es ein USB-Gerät gibt mit der in der Konfiguration definierten CPU
    matching_devices=($(ls /dev/serial/by-id/usb-Klipper_*"$cpu"*-if00 2>/dev/null))

    if [ ${#matching_devices[@]} -eq 1 ]; then
        serial="${matching_devices[0]}"
        echo "MCU found at $serial"
    elif [ ${#matching_devices[@]} -gt 1 ]; then
        echo "Error: Multiple MCUs found:"
        for device in "${matching_devices[@]}"; do
            echo "  - $device"
        done
        exit 1
    fi
fi

# Firmware flashen
if [ -e "$serial" ]; then
    echo "Flashing $serial..."
    sudo make flash FLASH_DEVICE=$serial > /dev/null 2>&1

    # Warten auf MCU-Neustart nach dem ersten Flash-Versuch
    if wait_for_mcu_reboot "$board"; then
        echo "Flashing successful."
        exit 0
    fi
fi

# Wenn kein Serial-Flash möglich ist, DFU-Modus versuchen
echo "Cannot Flash Board through serial mode, trying DFU mode..."
echo "Please Reboot your $board in DFU mode..."

# Maximale Wartezeit in Sekunden
MAX_WAIT=300
elapsed=0

# Schleife für maximal 300 Sekunden
while [ $elapsed -lt $MAX_WAIT ]; do
    # lsusb ausführen und prüfen, ob "Device in DFU Mode" enthalten ist
    OUTPUT=$(lsusb | grep "Device in DFU Mode")
    
    if [ -n "$OUTPUT" ]; then
        # ID aus der Ausgabe extrahieren
        serial=$(echo "$OUTPUT" | awk '{print $6}')
        echo "MCU found at $serial"
        echo "Flashing $serial..."
        sudo make flash FLASH_DEVICE=$serial > /dev/null 2>&1

        # Warten auf MCU-Neustart nach dem ersten Flash-Versuch
        if wait_for_mcu_reboot "$board"; then
            echo "Flashing successful."
            exit 0
        else
            # Prüfen ob Board immer noch im DFU Modus
            OUTPUT=$(lsusb | grep "Device in DFU Mode")
            if [ -n "$OUTPUT" ]; then
                echo "Board still in DFU, reflashing..."
                # ID aus der Ausgabe extrahieren
                serial=$(echo "$OUTPUT" | awk '{print $6}')
                sudo make flash FLASH_DEVICE=$serial > /dev/null 2>&1

                # Warten auf MCU-Neustart nach dem ersten Flash-Versuch
                if wait_for_mcu_reboot "$board"; then
                    echo "Flashing successful."
                    exit 0
                else
                    echo "Flashing failed."
                    exit 1
                fi
            fi
        fi
    fi

    # Eine Sekunde warten
    sleep 1
    ((elapsed++))
done

echo "No board found in DFU Mode, exiting"
exit 1


popd > /dev/null || exit