import logging

from pyftdi.pyftdi.ftdi import Ftdi
from pyftdi.serialext.ftdiext import SerialFtdi

from messages import *

logger = logging.getLogger(__name__)


class Hardware:
    def __init__(self):
        logger.debug("Searching for HiSPARC III Master...")
        master_url = self.get_master_url()
        if not master_url:
            raise RuntimeError("HiSPARC III Master not found")
        logger.debug("Master found at %s" % master_url)
        self.master = SerialFtdi(master_url, timeout=3)
        self.init_hardware(self.master)
        logger.info("HiSPARC III Master initialized")

    def get_master_url(self):
        devices = Ftdi.find_all([(0x403, 0x6010)])
        for device in devices:
            vendor_id, product_id, serial_str, num_interfaces, \
                description = device
            if description == "HiSPARC III Master":
                return "ftdi://ftdi:2232:%s/2" % serial_str
        return None

    def init_hardware(self, device):
        messages = [ResetMessage(True), InitializeMessage(True)]

        for message in messages:
            device.write(message.encode())
