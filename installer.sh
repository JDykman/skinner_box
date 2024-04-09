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

