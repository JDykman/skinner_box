#!/bin/bash

#Running the script
# Determine the directory where this script resides
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"
logs = "$SCRIPT_DIR/logs"
chmod 755 logs
# Now, run your Python script with sudo privileges using the dynamic path
echo "Running  with sudo privileges from the same directory..."
sudo python3 "$SCRIPT_DIR/skinnerBox.py"
