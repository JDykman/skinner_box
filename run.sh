#!/bin/bash

#Check to make sure packages are installed
ensure_package_installed() {
    PACKAGE_NAME=$1
    pip show $PACKAGE_NAME &> /dev/null
    if [ $? -ne 0 ]; then
        echo "Python package $PACKAGE_NAME is not installed. Installing..."
        sudo pip install $PACKAGE_NAME --break-system-packages
    else
        echo "Python package $PACKAGE_NAME is installed."
    fi
}

#List of required packages
required_packages=("flask" "rpi_ws281x" "gpiozero")

for package in "${required_packages[@]}"; do
	ensure_package_installed $package
done

#Running the script

# Determine the directory where this script resides
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

# Now, run your Python script with sudo privileges using the dynamic path
echo "Running  with sudo privileges from the same directory..."
sudo python3 "$SCRIPT_DIR/skinnerBox.py"

#!/bin/bash

#Set motor pin to pullup
gpio -g mode 18 out
gpio -g write 18 0

#Check to make sure packages are installed
ensure_package_installed() {
    PACKAGE_NAME=$1
    pip show $PACKAGE_NAME &> /dev/null
    if [ $? -ne 0 ]; then
        echo "Python package $PACKAGE_NAME is not installed. Installing..."
        sudo pip install $PACKAGE_NAME --break-system-packages
    else
        echo "Python package $PACKAGE_NAME is installed."
    fi
}

#List of required packages
required_packages=("flask" "rpi_ws281x" "gpiozero")

for package in "${required_packages[@]}"; do
	ensure_package_installed $package
done

#Running the script

# Determine the directory where this script resides
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

# Now, run your Python script with sudo privileges using the dynamic path
echo "Running  with sudo privileges from the same directory..."
sudo python3 "$SCRIPT_DIR/skinnerBox.py"
