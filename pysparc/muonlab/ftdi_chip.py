import pylibftdi


class DeviceNotFoundError(Exception):
    def __init__(self, msg):
        self.ftdi_msg = msg

    def __str__(self):
        return "Device not found"


class FtdiChip(object):

    def __init__(self, device_description=None):
        try:
            self._device = pylibftdi.Device(device_description)
        except pylibftdi.FtdiError as e:
            raise DeviceNotFoundError(str(e))

    @staticmethod
    def find_all():
        return pylibftdi.Driver().list_devices()
