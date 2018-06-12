"""Access FTDI hardware.

Contents
--------

:class:`Error`
    Base error class.

:class:`DeviceNotFoundError`
    Raised when device is not connected.

:class:`DeviceError`
    Raised for generic pylibftdi exceptions.

:class:`ReadError`
    Raised on read errors.

:class:`WriteError`
    Raised on write errors.

:class:`FtdiChip`
    Access FTDI hardware.

"""

import logging
import time

import pylibftdi


logger = logging.getLogger(__name__)


# FTDI documentation: must be multiple of block size, which is 64 bytes
# with 2 bytes overhead.  So, must be multiple of 62 bytes.
READ_SIZE = 62

# Default buffer size is 4K (64 * 64 bytes), but mind the overhead
# But this was not enough to clear all buffers. To be safe, for now, increase
# it ten-fold.
BUFFER_SIZE = 10 * 64 * 62

# Sleep between read/write error retries in seconds
RW_ERROR_WAIT = .5

# parity for rs232 line settings in libftdi::ftdi_set_line_property
PARITY_NONE = 0
PARITY_ODD = 1
PARITY_EVEN = 2
PARITY_MARK = 3
PARITY_SPACE = 4

# bitsize for rs232 line settings in libftdi::ftdi_set_line_property
BITS_8 = 8
BITS_7 = 7

# stopbits for rs232 line settings in libftdi::ftdi_set_line_property
STOP_BIT_1 = 0
STOP_BIT_15 = 1
STOP_BIT_2 = 2


class Error(Exception):

    """Base error class."""

    def __init__(self, msg):
        self.ftdi_msg = msg


class DeviceNotFoundError(Error):

    """Raised when device is not connected."""

    def __str__(self):
        return "Device not found."


class DeviceError(Error):

    """Raised for generic pylibftdi exceptions."""

    def __str__(self):
        return "Device error: %s" % self.ftdi_msg


class ClosedDeviceError(Error):

    """Raised when trying a read/write operation if device is closed."""

    def __str__(self):
        return "Device is closed, %s" % self.ftdi_msg


class ReadError(Error):

    """Raised on read errors."""

    def __str__(self):
        return "Device read error: %s" % self.ftdi_msg


class WriteError(Error):

    """Raised on write errors."""

    def __str__(self):
        return "Device write error: %s" % self.ftdi_msg


class FtdiChip(object):

    """Access FTDI hardware.

    Instantiate this class to get access to connected FTDI hardware.
    The hardware device is opened during instantiation.

    You can use the :meth:`find_all` static method to list all connected
    devices before openening them::

        >>> FtdiChip.find_all()

    """

    _device = None
    closed = True

    def __init__(self, device_description=None, interface_select=0):
        self._device_description = device_description
        self._interface_select = interface_select
        self.open()

    def open(self):
        """Open device.

        Raises :class:`DeviceNotFoundError` if the device cannot be found.
        Raises :class:`DeviceError` if the device cannot be opened.

        """
        if self._device is None:
            try:
                self._device = pylibftdi.Device(self._device_description,
                    interface_select=self._interface_select)
            except pylibftdi.FtdiError as exc:
                if "(-3)" in str(exc):
                    raise DeviceNotFoundError(str(exc))
                else:
                    raise DeviceError(str(exc))
            else:
                # force default latency timer of 16 ms
                # on some systems, this reverts to 0 ms if not set explicitly
                self._device.ftdi_fn.ftdi_set_latency_timer(16)

                self.closed = False
                self.flush()
        else:
            return

    def __del__(self):
        self.close()

    def set_line_settings(self, bits, parity, stop_bit):
        """Set line settings (bits, parity, stop bit).

        :param bits: one of BITS_8 or BITS_7
        :param parity: one of PARITY_NONE, PARITY_ODD, PARITY_EVEN,
                       PARITY_MARK, PARITY_SPACE
        :param stop_bit: one of STOP_BIT_1, STOP_BIT_15, STOP_BIT_2

        """
        self._device.ftdi_fn.ftdi_set_line_property(bits, stop_bit, parity)

    def close(self):
        """Close device."""

        if not self.closed:
            self._device.close()
            self._device = None
            self.closed = True

    @staticmethod
    def find_all():
        """Find all connected FTDI devices.

        :returns: list of (manufacturer, description, serial#) tuples.

        """
        return pylibftdi.Driver().list_devices()

    def flush(self):
        """Flush device buffers.

        To completely clear out outdated measurements, e.g. when changing
        parameters, call this method.  All data received after this method
        is called is really newly measured.

        """
        self._device.flush()
        self.read(BUFFER_SIZE)

    def read(self, read_size=None):
        """Read from device and retry if necessary.

        A read is tried three times.  When unsuccesful, raises
        :class:`ReadError`.  Raises :class:`ClosedDeviceError` when
        attempting to read from a closed device.

        :param read_size: number of bytes to read (defaults to READ_SIZE).
            As per the FTDI documentation, this should be a multiple of 62
            for best performance.

        :returns: string containing the data.

        """
        if self.closed:
            logger.warning("Attempting to read from closed device.")
            raise ClosedDeviceError("attempting to read.")

        if not read_size:
            read_size = READ_SIZE

        for i in range(3):
            try:
                data = self._device.read(read_size)
            except pylibftdi.FtdiError as exc:
                logger.warning("Read failed, retrying...")
                time.sleep(RW_ERROR_WAIT)
                continue
            else:
                return data
        logger.error("Read failed.")
        self.close()
        raise ReadError(str(exc))

    def write(self, data):
        """Write to device and retry if necessary.

        A write is tried three times.  When unsuccesful, raises
        :class:`WriteError`.  Raises :class:`ClosedDeviceError` when
        attempting to write from a closed device.

        :param data: string containing the data to write.

        """
        if self.closed:
            logger.warning("Attempting to read from closed device.")
            raise ClosedDeviceError("attempting to write.")

        for i in range(3):
            try:
                self._device.write(data)
            except pylibftdi.FtdiError as exc:
                logger.warning("Write failed, retrying...")
                time.sleep(RW_ERROR_WAIT)
                continue
            else:
                return
        logger.error("Write failed.")
        self.close()
        raise WriteError(str(exc))
