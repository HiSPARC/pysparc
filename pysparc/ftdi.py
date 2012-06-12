from pyftdi.pyftdi.ftdi import Ftdi
from pyftdi.serialext.ftdiext import SerialFtdi


FTDI_VENDOR_ID = 0x403
FTDI_PRODUCT_ID = 0x6010
PRODUCT_DESCRIPTION = '2232'


class FtdiChip:
    def __init__(self, serial_str):
        url = "ftdi://ftdi:%s:%s/2" % (PRODUCT_DESCRIPTION, serial_str)
        self.device = SerialFtdi(url, timeout=2)
        self.serial = serial_str

    @staticmethod
    def find_all():
        devices = Ftdi.find_all([(FTDI_VENDOR_ID, FTDI_PRODUCT_ID)])
        return [(serial_str, description) for
                vendor_id, product_id, serial_str, num_interfaces,
                description in devices]

    def write(self, data):
        return self.device.write(data)
