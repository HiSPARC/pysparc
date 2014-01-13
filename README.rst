PySPARC
=======

PySPARC is a data acquisition system for the HiSPARC experiment,
implemented in Python.  Ramon Kleiss came up with the excellent name.
Please note that this repository is by no means intended as a replacement
for the LabVIEW DAQ we currently have in operation.  It was, at first,
merely intended as a test bed.  Later, work was started on a MuonLab
application.  This was done to be able to remote control a running muonlab
experiment.  An event display is possible with an HTTP interface.


Prerequisites
-------------

HiSPARC III
^^^^^^^^^^^

* `libusb <http://www.libusb.org/>`_
* `PyUSB <https://github.com/walac/pyusb>`_
* `PyFTDI <https://github.com/eblot/pyftdi>`_


Muonlab II
^^^^^^^^^^

* `libusbx <http://libusbx.org>`_
* `libftdi <http://www.intra2net.com/en/developer/libftdi/>`_
* `pylibftdi <https://bitbucket.org/codedstructure/pylibftdi>`_

I like the fact that we do not depend on FTDI drivers or libraries.  We
were using PyFTDI for HiSPARC III, but were running into strange problems.
Pylibftdi / libftdi might be a more stable combination.


Status
------

Alpha.


Outlook
-------

At the time of this writing (early 2014), there is some activity.  I (DF)
am planning on using this code to work out an event display and teaching
materials for high school students.
