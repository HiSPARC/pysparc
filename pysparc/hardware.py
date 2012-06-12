import logging

from ftdi import FtdiChip


logger = logging.getLogger(__name__)


class Hardware:
    def __init__(self):
        logger.debug("Searching for HiSPARC III Master...")
        master = self.get_master()
        if not master:
            raise RuntimeError("HiSPARC III Master not found")
        logger.debug("Master found at %s" % master.serial)
        self.init_hardware(master)
        self.master = master
        logger.info("HiSPARC III Master initialized")

    def get_master(self):
        serial = self.get_master_serial()
        if serial:
            return FtdiChip(serial)
        else:
            return None

    def get_master_serial(self):
        devices = FtdiChip.find_all()
        for device in devices:
            serial_str, description = device
            if description == "HiSPARC III Master":
                return serial_str
        return None

    def init_hardware(self, device):
        device.write('\x99\xff\x66')
        device.write('\x99\x35\x00\x00\x00\x01\x66')
