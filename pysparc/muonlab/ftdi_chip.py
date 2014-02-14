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
BUFFER_SIZE = 64 * 62

# Sleep between read/write error retries in seconds
RW_ERROR_WAIT = .5


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

    def __init__(self, device_description=None):
        self._device_description = device_description
        self.open()

    def open(self):
        """Open device.

        Raises :class:`DeviceNotFoundError` if the device cannot be found.
        Raises :class:`DeviceError` if the device cannot be opened.

        """
        if self._device is None:
            try:
                self._device = pylibftdi.Device(self._device_description)
            except pylibftdi.FtdiError as exc:
                if "(-3)" in str(exc):
                    raise DeviceNotFoundError(str(exc))
                else:
                    raise DeviceError(str(exc))
            else:
                self.closed = False
                self.flush()
        else:
            return

    def __del__(self):
        self.close()

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
        :class:`ReadError`.

        :param read_size: number of bytes to read (defaults to READ_SIZE).

        :returns: string containing the data.

        """
        if not read_size:
            read_size = READ_SIZE

        if self.closed:
            self.open()

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
        :class:`WriteError`.

        :param data: string containing the data to write.

        """
        if self.closed:
            self.open()

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
