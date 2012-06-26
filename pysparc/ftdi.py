import logging

from pyftdi.pyftdi import ftdi
from pyftdi.pyftdi.ftdi import Ftdi
from pyftdi.serialext.ftdiext import SerialFtdi


logger = logging.getLogger(__name__)


FTDI_VENDOR_ID = 0x403
FTDI_PRODUCT_ID = 0x6010
PRODUCT_DESCRIPTION = '2232'


class FtdiChip:
    device = None

    def __init__(self, serial_str):
        self.serial = serial_str
        self.get_device()
        self.flush_input()

    @staticmethod
    def find_all():
        devices = Ftdi.find_all([(FTDI_VENDOR_ID, FTDI_PRODUCT_ID)])
        return [(serial_str, description) for
                vendor_id, product_id, serial_str, num_interfaces,
                description in devices]

    def get_device(self):
        url = "ftdi://ftdi:%s:%s/2" % (PRODUCT_DESCRIPTION, self.serial)
        if self.device is not None:
            self.device.close()
        self.device = SerialFtdi(url, timeout=.001)

    def write(self, data):
        return self.device.write(data)

    def read(self, length):
        """Read data from device

        Read data from device, and catch one level of spurious empty
        errors.

        """
        try:
            data = self.device.read(length)
        except ftdi.FtdiError as exc:
            logger.warning("Spurious PyFTDI 'None' error, recovering...")
            if '[Errno None]' in exc.message:
                self.get_device()
                data = self.device.read(length)
                return data
            else:
                raise
        else:
            return data
        raise Exception("Programming error.  I should not be here.")

    def flush_input(self):
        while self.read(64 * 1024):
            logger.info("Flushed input buffer")

    def close(self):
        self.device.close()
