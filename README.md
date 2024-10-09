This code is the code running on a skinnerbox.

For First Time Setup:

1. Download and unzip the file on rasperry pi
2. Run the installer.sh file. This will import all the necesarry packages.
3. Run the program by using the run.sh file or run.py

Setting up Crontab
1. Open a console tab and enter 'crontab -e'
2. Scroll to the bottom and enter the command '' #TODO

Setting Up Network: (Planned to change in future)
1. Navigate to the network tab in the top right
2. Left click and go to Advanced Connections -> Edit Connections -> Wired Connection 1 -> Settings -> IPv4 Settings
3. Set Method to Manual
4. Under "Additional Static Addresses" click add
5. Open a command terminal and type "ifconfig" 
6. Back in the Network Connection set the Address to the inet in the terminal (Alternatively set it to a custom value)
7. Set the Netmask to the netmask
8. Set Gateway to the broadcast
