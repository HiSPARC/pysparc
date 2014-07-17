import logging
import time
import random

import ftdi_chip
from ftdi_chip import FtdiChip
from messages import (HisparcMessageFactory, ResetMessage,
                      InitializeMessage, MeasuredDataMessage)
import config


logger = logging.getLogger(__name__)


READSIZE = 64 * 1024


class HiSPARCIII(object):

    """Access HiSPARC III hardware.

    Instantiate this class to get access to connected HiSPARC III hardware.
    The hardware device is opened during instantiation.

    """

    description = "HiSPARC III Master"
    _device = None
    _buffer = None

    def __init__(self):
        # open device's second interface (DAQ)
        self._device = FtdiChip(self.description, interface_select=2)
        self._buffer = bytearray()
        self.config = config.Config(self)
        self.reset_hardware()

    def __del__(self):
        self.close()

    def close(self):
        """Close the hardware device."""

        if self._device and not self._device.closed:
            self._device.close()

    def flush_device(self):
        """Flush device output buffers.

        To completely clear out outdated measurements when changing
        parameters, call this method.  All data received after this method
        was called is really newly measured.

        """
        self._device.flush()
        del self._buffer[:]

    def reset_hardware(self):
        """Reset the hardware device."""

        self.send_message(ResetMessage())
        self.send_message(InitializeMessage())

    def send_message(self, msg):
        """Send a message to the hardware device."""

        self._device.write(msg.encode())

    def read_into_buffer(self):
        """Read data from device and place it in the read buffer.

        Call this method to empty the device and host usb buffer.  All
        data is read into the class instance's data buffer.  It is not
        necessary to call this method in your program, unless you need to
        make sure the usb buffers won't fill up while running long tasks.
        If you just want to read messages from the device, use the
        appropriate methods.  This method is called by those methods.

        """
        data = self._device.read(ftdi_chip.BUFFER_SIZE)
        self._buffer.extend(data)

    def read_message(self):
        """Read a message from the hardware device.

        Call this method to communicate with the device.

        :returns: a :class:`pysparc.messages.HisparcMessage` subclass
            instance

        """
        self.read_into_buffer()
        return HisparcMessageFactory(self._buffer)

    def flush_and_get_measured_data_message(self, timeout=15):
        """Flush output buffers and wait for measured data.

        This method is useful if you want to change device parameters and
        then measure the effect on the data.  To make sure that the data
        is actually taken *after* changing the parameters, the output
        buffers are flushed before a measured data message is returned.

        The alignment procedure makes use of this method.

        :param timeout: maximum time in seconds to wait for message
        :returns: a :class:`pysparc.messages.MeasuredDataMessage`
            instance or None if a timeout occured.

        """
        self.flush_device()
        t0 = time.time()
        while time.time() - t0 < timeout:
            msg = self.read_message()
            if isinstance(msg, MeasuredDataMessage):
                return msg
