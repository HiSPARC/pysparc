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


Creating the disk image for provisioning a Raspberry Pi
-------------------------------------------------------

Perform the following steps:

#. Download the latest raspbian image from
   http://www.raspberrypi.org/downloads/ and rename it to ``pysparc.img``.
   Place the image in the root of this repository, which makes it
   available to the vagrant VM.  Unfortunately, it is not possible to use
   a Mac to have read/write access to the ext4 filesystem in the image.
#. Download the VPN certificate for the host *newpi* and place the
   certificate in the root of this repository as ``vpncert.zip``.
#. Enter the VM using::

      $ vagrant ssh

#. Because the image is a full disk image containing partitions, it is
   slightly nontrivial.  Setting up the disk image involves some work, as
   well.  We've created a script which takes care of everything::

      $ sh /vagrant/provisioning/provision_image.sh
