import logging
import time
import random

from ftdi_chip import FtdiChip
import messages
from messages import *
from config import *


logger = logging.getLogger(__name__)


READSIZE = 64 * 1024


class Hardware:
    master = None

    def __init__(self):
        logger.info("Searching for HiSPARC III Master...")
        master = self.get_master()
        if not master:
            raise RuntimeError("HiSPARC III Master not found")
        logger.info("Master found")
        self.init_hardware(master)
        self.master = master
        self.master_buffer = bytearray()
        self.config = Config(self)
        logger.info("HiSPARC III Master initialized")

    def get_master(self):
        return FtdiChip("HiSPARC III Master", interface_select=2)

    def init_hardware(self, device):
        messages = [ResetMessage(), InitializeMessage(True)]

        for message in messages:
            device.write(message.encode())

    def flush_and_get_measured_data_message(self):
        self.master.flush()
        while True:
            msg = self.read_message()
            if type(msg) == messages.MeasuredDataMessage:
                break
        return msg

    def read_message(self):
        self.read_data_into_buffer()
        if not len(self.master_buffer):
            time.sleep(.1)
        return HisparcMessageFactory(self.master_buffer)

    def read_data_into_buffer(self):
        input_buff = self.master.read(READSIZE)
        self.master_buffer.extend(input_buff)

    def send_message(self, msg):
        self.master.write(msg.encode())

    def close(self):
        if self.master:
            self.master.write(ResetMessage().encode())
            time.sleep(1)
            self.master.flush()
            self.master.close()
        self._closed = True

    def __del__(self):
        if not self.__dict__.get('_closed'):
            self.close()
