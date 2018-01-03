#!/bin/sh

USER_NAME=pi
USER_UID=1000
USER_GID=1000
MOUNT_POINT=/mnt
IMG=/vagrant/pysparc.img
HOME_DIR=$MOUNT_POINT/home/$USER_NAME
OPENVPN_DIR=$MOUNT_POINT/etc/openvpn

# Setup loopback interface for the image file
sudo modprobe -r loop
sudo modprobe loop max_part=63
sudo losetup /dev/loop0 $IMG

# If successful, mount the boot disk
if [ -b /dev/loop0p1 ]
then
  sudo mount /dev/loop0p1 $MOUNT_POINT
else
  echo "Unfortunately, there was a problem creating the loop device."
  echo "Please re-run this script."
  sudo losetup -d /dev/loop0
  exit 1
fi

# Enable the SSH server
sudo touch $MOUNT_POINT/ssh

# Unmount the boot disk
sudo umount $MOUNT_POINT

# If successful, mount the system disk
if [ -b /dev/loop0p2 ]
then
  sudo mount /dev/loop0p2 $MOUNT_POINT
else
  echo "Unfortunately, there was a problem creating the loop device."
  echo "Please re-run this script."
  sudo losetup -d /dev/loop0
  exit 1
fi

# If the home directory exists, add SSH keys
if [ -d $HOME_DIR ]
then
  if [ ! -d $HOME_DIR/.ssh ]; then sudo mkdir $HOME_DIR/.ssh; fi
  sudo cp /vagrant/provisioning/authorized_keys $HOME_DIR/.ssh
  sudo chown -R 1000:1000 $HOME_DIR/.ssh
else
  echo "Home directory could not be found in image."
fi

# Copy the VPN config and certificates
if [ ! -d $OPENVPN_DIR ]; then sudo mkdir $OPENVPN_DIR; fi
sudo cp /vagrant/provisioning/hisparcvpn.conf $OPENVPN_DIR
sudo cp /vagrant/vpncert.zip $OPENVPN_DIR

# Setup the first boot script
sudo cp --preserve=mode /vagrant/provisioning/firstboot.sh $MOUNT_POINT/etc/rc.local

# Unmount the disk
sudo umount $MOUNT_POINT
sudo losetup -d /dev/loop0
