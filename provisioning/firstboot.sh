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

# Systemd executes this script after the network is up. However, it still needs
# a bit more time, so make sure apt-get is retried
# Install OpenVPN
until apt-get update && yes | apt-get install unzip openvpn;
do
  echo 'Retrying...'
  sleep 5
done

yes | unzip /etc/openvpn/vpncert.zip -d /etc/openvpn
service openvpn restart

exit 0
