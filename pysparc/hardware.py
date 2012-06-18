import logging
import time

from ftdi import FtdiChip
import messages
from messages import *
from config import *
from bracket import InvertedIntegerOptimization


logger = logging.getLogger(__name__)


READSIZE = 64 * 1024


class Hardware:
    master = None

    def __init__(self):
        logger.debug("Searching for HiSPARC III Master...")
        master = self.get_master()
        if not master:
            raise RuntimeError("HiSPARC III Master not found")
        logger.debug("Master found: %s" % master.serial)
        self.init_hardware(master)
        self.master = master
        self.master_buffer = bytearray()
        self.config = Config(self)
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

    def align_adcs(self):
        self.config.trigger_condition = 0x80
        self._align_full_scale()

    def _align_full_scale(self):
        logger.info("Aligning full scale")
        initial_guess = 0x80
        target_value = 2048
        is_done = False

        logger.debug("Initial guess: %d" % (initial_guess))
        self.config.full_scale = initial_guess
        mean_adc_value = self._get_mean_adc_value()
        logger.debug("Initial mean ADC value: %d" % mean_adc_value)

        a, b, c = 0, initial_guess, 0xff
        fa = target_value - 0
        fb = abs(mean_adc_value - target_value)
        fc = 4095 - target_value
        optimization = InvertedIntegerOptimization((a, b, c),
                                                   (fa, fb, fc))
        guess = optimization.first_step()
        while not is_done:
            self.config.full_scale = guess
            mean_adc_value = self._get_mean_adc_value()
            logger.debug("Alignment step (guess, mean): %d, %d" %
                         (guess, mean_adc_value))
            f_guess = abs(mean_adc_value - target_value)
            guess, is_done = optimization.next_step(f_guess)
        logger.info("Full scale aligned (guess, mean): %d, %d" %
                    (guess, mean_adc_value))
        self.config.full_scale = guess

    def _get_mean_adc_value(self):
        msg = self.get_measured_data_message()
        mean_value = (msg.trace_ch1.mean() + msg.trace_ch2.mean()) / 2
        return mean_value

    def get_measured_data_message(self):
        while True:
            msg = self.read_message()
            if type(msg) == messages.MeasuredDataMessage:
                break
        return msg

    def read_message(self):
        self.read_data_into_buffer()
        return HisparcMessageFactory(self.master_buffer)

    def read_data_into_buffer(self):
        input_buff = self.master.read(READSIZE)
        self.master_buffer.extend(input_buff)

    def send_message(self, msg):
        self.master.write(msg.encode())

    def close(self):
        if self.master:
            self.master.write(ResetMessage(True).encode())
            time.sleep(1)
            self.master.flush_input()
            self.master.close()
        self._closed = True

    def __del__(self):
        if not self.__dict__.get('_closed'):
            self.close()
