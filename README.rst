PySPARC
=======

PySPARC is a data acquisition system for the HiSPARC experiment,
implemented in Python.  Ramon Kleiss came up with the excellent name.

Please note that this repository was, at first, by no means intended as a
replacement for the LabVIEW DAQ we currently have in operation.  It was
merely intended as a test bed.  Later, work was started on a MuonLab
application.  This was done to be able to remote control a running muonlab
experiment.  An event display is possible with an HTTP interface.

Currently, we're looking into replacing our LabVIEW / Windows PC setup
with a Raspberry Pi running PySPARC.


Prerequisites
-------------

* `libusb <http://libusb.info>`_
* `libftdi <http://www.intra2net.com/en/developer/libftdi/>`_
* `pylibftdi <https://bitbucket.org/codedstructure/pylibftdi>`_

I like the fact that we do not depend on FTDI drivers or closed-source
libraries.  We were using PyFTDI for HiSPARC III, but were running into
strange problems. Pylibftdi / libftdi is proving to be a more stable
combination.


Status
------

Alpha, but getting there.


Outlook
-------

At the time of this writing (mid-2014), there is renewed activity.  We're
testing this code on a Raspberry Pi with the goal of replacing our old
Windows PC's.  They are a pain to maintain.

I (DF) am also planning on using this code to work out an event display
and teaching materials for high school students.  This will focus on the
muon lifetime experiment. However, there already exists a LabVIEW
interface and a new LabVIEW interface is in development for driving the
Muonlab III hardware.


Updating the Raspberry Pi's
---------------------------

We use Ansible to keep all Raspberry Pi's up to date. Run the Ansible commands
from the directory containing the ``ansible.cfg`` file. That is, the project
root directory.

To update all machines (dev and production), run::

    $ ansible-playbook provisioning/playbook.yml

To update only the machines in the ``dev`` group, run::

    $ ansible-playbook provisioning/playbook.yml -l dev


Running isolated commands on the Raspberry Pi's
-----------------------------------------------

You can use Ansible to connect to a raspberry pi and run a command. Like so::

    $ ansible \* -a "supervisorctl status"

The ``\*`` selects *all* machines. To limit the command to ``dev`` boxes, run::

    $ ansible dev -a "supervisorctl status"


Creating the disk image for provisioning a Raspberry Pi
-------------------------------------------------------

Perform the following steps:

#. Download the latest raspbian image from
   http://www.raspberrypi.org/downloads/ and rename it to ``pysparc.img``.
   Place the image in the root of this repository, which makes it
   available to the vagrant VM.  Unfortunately, it is not possible to use
   a Mac to have read/write access to the ext4 filesystem in the image.
   Note that we're not using the image as a VM!  We're using the
   pre-existing vagrant VM to *access* the image file.
#. Download the VPN certificate for the host *newpi* and place the
   certificate in the root of this repository as ``vpncert.zip``.
#. Enter the VM using::

      $ vagrant ssh

#. Because the image is a full disk image containing partitions, it is
   slightly nontrivial.  Setting up the disk image involves some work, as
   well.  We've created a script which takes care of everything::

      $ sh /vagrant/provisioning/provision_image.sh

   You can now use this image for multiple installs.


Writing the disk image
----------------------

In a shell, back on your Mac::

   $ diskutil list
   /dev/disk1
      #:                       TYPE NAME                    SIZE       IDENTIFIER
      0:     FDisk_partition_scheme                        *8.0 GB     disk1
      1:             Windows_FAT_32 boot                    58.7 MB    disk1s1
      2:                      Linux                         3.2 GB     disk1s2
   $ diskutil unmountdisk disk1
   $ sudo dd if=pysparc.img of=/dev/rdisk1 bs=1m
   $ diskutil eject disk1


Provisioning the new system
---------------------------

Once the device has booted, it will install OpenVPN, unzip the
certificates and connect to the HiSPARC VPN network, as ``newpi``. *Make
sure that you only boot one new device at a time, since otherwise multiple
devices will connect as* ``newpi`` *, resulting in VPN disconnects.* You
can simply logon using SSH, download the final certificate, unzip it and
restart OpenVPN::

   $ cd /etc/openvpn
   $ sudo unzip <path_to_certificate>
   <choose overwrite all>
   $ sudo service openvpn restart

The connection will be immediately dropped, but can be restored by
connecting using the new hostname.  Add the new host to the Ansible
inventory file and run the playbook.


Troubleshooting
---------------

Run command across all pysparc installations::

   (localhost) $ ansible pysparc -a "<insert command here>"

Query the NTP daemon::

   $ ntpq -p

Scan for filtered NTP port::

   $ sudo nmap -PN -sU -p ntp time.apple.com
