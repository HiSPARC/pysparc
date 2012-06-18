import logging
import time

from ftdi import FtdiChip
import messages
from messages import *
from config import *
from bracket import InvertedIntegerOptimization, \
                    ParallelInvertedIntegerOptimization


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
        # FIXME: sometimes alignment steps and messages are not
        # synchronized
        self._reset_config_for_alignment()
        self.config.trigger_condition = 0x80
        self._align_full_scale()
        self._align_common_offset()
        #self._align_individual_offsets()

    def _reset_config_for_alignment(self):
        self.config.full_scale = 0x80
        self.config.common_offset = 0x80

    def _align_full_scale(self):
        logger.info("Aligning full scale")
        opt_value = self._align_offset(self._set_full_scale, 0x80)
        logger.info("Full scale aligned (value): %d" % opt_value)

    def _set_full_scale(self, value):
        self.config.full_scale = value

    def _align_common_offset(self):
        logger.info("Aligning common offset")
        opt_value = self._align_offset(self._set_common_offset, 0x80)
        logger.info("Common offset aligned (value): %d" % opt_value)

    def _set_common_offset(self, value):
        self.config.common_offset = value

    def _align_offset(self, set_offset_func, initial_guess):
        target_value = 2048
        is_done = False

        a, b, c = 0, initial_guess, 0xff
        fa, fb, fc = [self._measure_opt_value_at_offset(set_offset_func,
                                                        u, target_value)
                      for u in a, b, c]
        optimization = InvertedIntegerOptimization((a, b, c),
                                                   (fa, fb, fc))
        guess = optimization.first_step()
        while not is_done:
            f_guess = self._measure_opt_value_at_offset(
                        set_offset_func, guess, target_value)
            guess, is_done = optimization.next_step(f_guess)
        set_offset_func(guess)
        return guess

    def _measure_opt_value_at_offset(self, set_offset_func, guess,
                                     target):
        set_offset_func(guess)
        mean_adc_value = self._get_mean_adc_value()
        logger.debug("Alignment step (guess, mean): %d, %d" %
                     (guess, mean_adc_value))
        return abs(target - mean_adc_value)

    def _align_individual_offsets(self):
        logger.info("Aligning individual offsets")
        initial_guesses = [0x80] * 4
        target_value = 2048
        is_all_done = [False] * 4

        a, b, c = [0] * 4, initial_guesses, [0xff] * 4
        fa, fb, fc = [self._measure_opt_value_at_individual_offsets(
                        u, target_value) for u in a, b, c]
        optimization = ParallelInvertedIntegerOptimization((a, b, c),
                                                           (fa, fb, fc))
        guesses = optimization.first_step()
        while not sum(is_all_done) == 4:
            f_guesses = self._measure_opt_value_at_individual_offsets(
                            guesses, target_value)
            guesses, is_all_done = optimization.next_step(f_guesses)
        logger.info("Offset aligned (value): %d %d %d %d" % guesses)
        self._set_individual_offsets(guesses)

    def _measure_opt_value_at_individual_offsets(self, guesses, target):
        self._set_individual_offsets(guesses)
        msg = self.get_measured_data_message()
        mean_adc_values = (msg.adc_ch1_pos.mean(), msg.adc_ch1_neg.mean(),
                           msg.adc_ch2_pos.mean(), msg.adc_ch2_neg.mean())
        logger.debug("Alignment step (guesses, means):\n\t%s, %s" %
                     (guesses, [int(round(u)) for u in mean_adc_values]))
        return [abs(target - u) for u in mean_adc_values]

    def _set_individual_offsets(self, offsets):
        (self.config.channel1_offset_positive,
         self.config.channel1_offset_negative,
         self.config.channel2_offset_positive,
         self.config.channel2_offset_negative) = offsets

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
