"""Access HiSPARC hardware.

Contents
--------

:class:`HiSPARCIII`
    Access HiSPARC III hardware.

"""

import logging
import time
import random

import ftdi_chip
from ftdi_chip import FtdiChip
from messages import (HisparcMessageFactory, ResetMessage,
                      InitializeMessage, MeasuredDataMessage)
import config

import pkg_resources


logger = logging.getLogger(__name__)


READ_SIZE = 1024 * 62
FPGA_BUFFER_SIZE = 64 * 1024

# FTDI MPSSE commands
SET_BITS_LOW = 0x80
GET_BITS_LOW = 0x81
SET_BITS_HIGH = 0x82
GET_BITS_HIGH = 0x83
TCK_DIVISOR = 0x86
DISABLE_CLK_DIV5 = 0x8A
WRITE_BYTES_PVE_LSB = 0x18


class HardwareError(Exception):

    """Raised on error with the hardware."""

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class HiSPARCIII(object):

    """Access HiSPARC III hardware.

    Instantiate this class to get access to connected HiSPARC III hardware.
    The hardware device is opened during instantiation.

    """

    description = "HiSPARC III Master"
    _device = None
    _buffer = None

    def __init__(self):
        self._burn_firmware()
        # device doesn't like to be reopened immediately after burning
        # firmware.
        time.sleep(.5)

        # open device's second interface (DAQ)
        self._device = FtdiChip(self.description, interface_select=2)
        self._buffer = bytearray()
        self.config = config.Config(self)
        self.reset_hardware()

    def __del__(self):
        self.close()

    def _burn_firmware(self):
        """Burn the firmware to the device's FPGA.

        This was a pain to implement.  Understanding this code entails
        going back and forth between the FTDI and Altera Cyclone manuals,
        as well as the the HiSPARC schematics.

        The Cyclone has 16 data bits (page 5 in the manual) of which
        several are general purpose I/O (GPIO).  The connections are up to
        the hardware designers.

        Connections FTDI <-> Cyclone (HiSPARC III hardware):

            bit 8:  nCONFIG
            bit 9:  CONF_DONE
            bit 10: nSTATUS

        Configuration of the FPGA is described on page 9-9 of the Cyclone
        manual. First, pull nCONFIG low (for at least 500 ns).  nSTATUS
        and CONF_DONE are also pulled low by the device.  Then, pull
        nCONFIG high and the device returns nSTATUS to high.

        If configuration is succesful, CONF_DONE is high.  If an error occurs,
        nSTATUS is pulled low and CONF_DONE remains low.

        On page 9-13 in the Cyclone manual, the connections between the
        serial configuration device (the FTDI chip) and the Cyclone are
        described, along with the data connection and clock settings (page
        9-14).


        References:

        Altera Cyclone III Device Handbook -- Volume 1
        FTDI Application Note AN_108 -- Command Processor for MPSSE and
            MCU Host Bus Emulation Modes


        Basic information on using MPSSE mode (useful for understanding
        the bitmode, clock settings and writing the data):

        FTDP Application Note AN_135 -- FTDI MPSSE Basics

        """
        # open device's first interface (MPSSE)
        device = FtdiChip(self.description, interface_select=1)

        # Select MPSSE mode (0x02)
        # Direction is not used here, it doesn't seem to work.
        # We'll set the direction explicitly later.
        device._device.ftdi_fn.ftdi_set_bitmode(0, 0x02)

        # Set clock frequency to 30 MHz (0x0000)
        device.write(bytearray([TCK_DIVISOR, 0, 0]))
        # Disable divide clock frequency by 5
        device.write(bytearray([DISABLE_CLK_DIV5]))

        # bits 0 and 1 are output that is, bits TCK/SK and TDI/DO, clock and
        # data
        device.write(bytearray([SET_BITS_LOW, 0, 0b11]))

        # pull nCONFIG (low byte bit 0) low
        device.write(bytearray([SET_BITS_HIGH, 0, 1]))
        # pull nCONFIG (low byte bit 0) high
        device.write(bytearray([SET_BITS_HIGH, 1, 1]))

        firmware = pkg_resources.resource_string(__name__, "firmware.rbf")
        for idx in range(0, len(firmware), FPGA_BUFFER_SIZE):
            xbuf = firmware[idx:idx + FPGA_BUFFER_SIZE]

            LENGTH = len(xbuf) - 1
            LENGTH_L = LENGTH & 0xff
            LENGTH_H = LENGTH >> 8 & 0xff
            device.write(bytearray([WRITE_BYTES_PVE_LSB, LENGTH_L, LENGTH_H]))
            device.write(xbuf)

        # read device status
        device.write(bytearray([GET_BITS_HIGH]))
        time.sleep(.01)
        data_bits = ord(device.read(1))

        # CONF_DONE is bit 8 (high byte, bit 1)
        conf_done = data_bits & 0b10
        if not conf_done:
            raise HardwareError("Error loading firmware.")

        device.close()

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
        self.config.reset_hardware()

    def send_message(self, msg):
        """Send a message to the hardware device."""

        logger.debug("Sending message: %s", msg)
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
        data = self._device.read(READ_SIZE)
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
