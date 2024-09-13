This code is a beta version of the code running on a skinnerbox.
Main Trunk: https://github.com/JDykman/skinner_box.git

For First Time Setup:

1. Download and unzip the file on rasperry pi
2. Run the install.sh file. This will import all the necesarry packages.

Setting Up Network:
1. Navigate to the network tab in the top right
2. Left click and go to Advanced Connections -> Edit Connections -> Wired Connection 1 -> Settings -> IPv4 Settings
3. Set Method to Manual
4. Under "Additional Static Addresses" click add
5. Open a command terminal and type "ifconfig" 
6. Back in the Network Connection set the Address to the inet in the terminal (Alternatively set it to a custom value)
7. Set the Netmask to the netmask
8. Set Gateway to the broadcast
