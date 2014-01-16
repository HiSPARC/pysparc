import pylibftdi


# FTDI documentation: must be multiple of block size, which is 64 bytes
# with 2 bytes overhead.  So, must be multiple of 62 bytes.
READ_SIZE = 62

# Default buffer size is 4K (64 * 64 bytes), but mind the overhead
BUFFER_SIZE = 64 * 62


class Error(Exception):

    def __init__(self, msg):
        self.ftdi_msg = msg


class DeviceNotFoundError(Error):

    def __str__(self):
        return "Device not found."


class DeviceError(Error):

    def __str__(self):
        return "Device error: %s" % self.ftdi_msg


class ReadError(Error):

    def __str__(self):
        return "Device read error: %s" % self.ftdi_msg


class WriteError(Error):

    def __str__(self):
        return "Device write error: %s" % self.ftdi_msg


class FtdiChip(object):

    _device = None

    def __init__(self, device_description=None):
        try:
            self._device = pylibftdi.Device(device_description)
        except pylibftdi.FtdiError as exc:
            if "(-3)" in str(exc):
                raise DeviceNotFoundError(str(exc))
            else:
                raise DeviceError(str(exc))
        else:
            self.flush_device()

    def __del__(self):
        if self._device:
            self.close()

    def close(self):
        self._device.close()

    @staticmethod
    def find_all():
        return pylibftdi.Driver().list_devices()

    def flush_device(self):
        self._device.flush()
        self._device.read(BUFFER_SIZE)

    def read(self):
        for i in range(3):
            try:
                data = self._device.read(READ_SIZE)
            except pylibftdi.FtdiError as exc:
                continue
            else:
                return data
        raise ReadError(str(exc))

    def write(self, data):
        for i in range(3):
            try:
                self._device.write(data)
            except pylibftdi.FtdiError as exc:
                continue
            else:
                return
        raise WriteError(str(exc))
