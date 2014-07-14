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

    _description = "HiSPARC III Master"
    _device = None
    _buffer = None

    def __init__(self):
        self._device = FtdiChip(self._description)
        self._buffer = bytearray()
        self.config = config.Config(self)

    def __del__(self):
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


class Hardware(object):
    master = None

    def __init__(self):
        logger.info("Searching for HiSPARC III Master...")
        master = self.get_master()
        if not master:
            raise RuntimeError("HiSPARC III Master not found")
        logger.info("Master found")
        self.init_hardware(master)
        self.master = master
        self.master_buffer = bytearray()
        self.config = config.Config(self)
        logger.info("HiSPARC III Master initialized")

    def get_master(self):
        return FtdiChip("HiSPARC III Master", interface_select=2)

    def init_hardware(self, device):
        messages = [ResetMessage(), InitializeMessage(True)]

        for message in messages:
            device.write(message.encode())

    def flush_and_get_measured_data_message(self):
        self.master.flush()
        while True:
            msg = self.read_message()
            if type(msg) == MeasuredDataMessage:
                break
        return msg

    def read_message(self):
        self.read_data_into_buffer()
        if not len(self.master_buffer):
            time.sleep(.1)
        return HisparcMessageFactory(self.master_buffer)

    def read_data_into_buffer(self):
        input_buff = self.master.read(READSIZE)
        self.master_buffer.extend(input_buff)

    def send_message(self, msg):
        self.master.write(msg.encode())

    def close(self):
        if self.master:
            self.master.write(ResetMessage().encode())
            time.sleep(1)
            self.master.flush()
            self.master.close()
        self._closed = True

    def __del__(self):
        if not self.__dict__.get('_closed'):
            self.close()
