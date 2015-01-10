#!/bin/sh

USER_NAME=pi
USER_UID=1000
USER_GID=1000
MOUNT_POINT=/mnt
IMG=/vagrant/pysparc.img
DIR=$MOUNT_POINT/home/$USER_NAME

sudo modprobe -r loop
sudo modprobe loop max_part=63
sudo losetup /dev/loop0 $IMG

if [ -b /dev/loop0p2 ]
then
  sudo mount /dev/loop0p2 $MOUNT_POINT
else
  echo "Unfortunately, there was a problem creating the loop device."
  echo "Please re-run this script."
  sudo losetup -d /dev/loop0
  exit 1
fi

if [ -d $DIR ]
then
  if [ ! -d $DIR/.ssh ]; then sudo mkdir $DIR/.ssh; fi
  sudo cp /vagrant/provisioning/authorized_keys $DIR/.ssh
  sudo chown -R 1000:1000 $DIR/.ssh
else
  echo "Home directory could not be found in image."
fi

if [ ! -d /etc/openvpn ]; then sudo mkdir /etc/openvpn; fi
sudo cp /vagrant/provisioning/hisparcvpn.conf /etc/openvpn
sudo cp /vagrant/vpncert.zip /etc/openvpn

sudo umount $MOUNT_POINT
sudo losetup -d /dev/loop0
