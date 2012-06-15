import logging
import time

from ftdi import FtdiChip


from messages import *

logger = logging.getLogger(__name__)


READSIZE = 64 * 1024


class Hardware:
    def __init__(self):
        logger.debug("Searching for HiSPARC III Master...")
        master = self.get_master()
        if not master:
            raise RuntimeError("HiSPARC III Master not found")
        logger.debug("Master found: %s" % master.serial)
        self.init_hardware(master)
        self.master = master
        self.master_buffer = bytearray()
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
        messages = [ResetMessage(True), InitializeMessage(True)]

        for message in messages:
            device.write(message.encode())

    def read_message(self):
        self.read_data_into_buffer()
        return HisparcMessageFactory(self.master_buffer)

    def read_data_into_buffer(self):
        input_buff = self.master.read(READSIZE)
        self.master_buffer.extend(input_buff)

    def send_message(self, msg):
        self.master.write(msg.encode())

    def close(self):
        self.master.write(ResetMessage(True).encode())
        time.sleep(1)
        self.master.flush_input()

    def __del__(self):
        self.close()
