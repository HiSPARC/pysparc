#!/bin/sh -e
#
# rc.local
#
# This script is executed at the end of each multiuser runlevel.
# Make sure that the script will "exit 0" on success or any other
# value on error.
#
# In order to enable or disable this script just change the execution
# bits.
#
# By default this script does nothing.

# Install OpenVPN
apt-get update
yes | apt-get install unzip openvpn
unzip /etc/openvpn/vpncert.zip -d /etc/openvpn
service openvpn restart

exit 0
