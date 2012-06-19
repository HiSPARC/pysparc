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
        logger.info("Searching for HiSPARC III Master...")
        master = self.get_master()
        if not master:
            raise RuntimeError("HiSPARC III Master not found")
        logger.info("Master found: %s" % master.serial)
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
        # FIXME: Initial guess 0x30 for 2nd full scale. Hmm.
        self._reset_config_for_alignment()
        self.config.trigger_condition = 0x80
        self._align_full_scale(2048)
        self._align_common_offset(2048)
        self._align_individual_offsets(2048)
        self._align_full_scale(200, 0x30)
        self._align_common_offset(200)
        self._align_individual_gains(200)

    def _reset_config_for_alignment(self):
        self._set_full_scale(0x80)
        self._set_common_offset(0x80)
        self._set_individual_offsets([0x80] * 4)

    def _align_full_scale(self, target_value, initial_guess=0x80):
        logger.info("Aligning full scale")
        opt_value = self._align_offset(self._set_full_scale,
                                       initial_guess, target_value)
        logger.info("Full scale aligned (value): %d" % opt_value)

    def _align_common_offset(self, target_value):
        logger.info("Aligning common offset")
        opt_value = self._align_offset(self._set_common_offset, 0x80,
                                       target_value)
        logger.info("Common offset aligned (value): %d" % opt_value)

    def _align_individual_offsets(self, target_value):
        logger.info("Aligning individual offsets")
        opt_values = self._align_individual_settings(
                        self._set_individual_offsets, [0x80] * 4,
                        target_value)
        logger.info("Individual offsets aligned (values): %d %d %d %d" %
                    opt_values)

    def _align_individual_gains(self, target_value):
        logger.info("Aligning individual gains")
        opt_values = self._align_individual_settings(
                        self._set_individual_gains, [0x80] * 4,
                        target_value)
        logger.info("Individual gains aligned (values): %d %d %d %d" %
                    opt_values)

    def _align_offset(self, set_offset_func, initial_guess, target_value):
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

    def _align_individual_settings(self, settings_func, initial_guesses,
                                   target_value):
        is_all_done = [False] * 4

        a, b, c = [0] * 4, initial_guesses, [0xff] * 4
        fa, fb, fc = [self._measure_opt_value_at_individual_settings(
                        settings_func, u, target_value) for
                      u in a, b, c]
        optimization = ParallelInvertedIntegerOptimization((a, b, c),
                                                           (fa, fb, fc))
        guesses = optimization.first_step()
        while not sum(is_all_done) == 4:
            f_guesses = self._measure_opt_value_at_individual_settings(
                            settings_func, guesses, target_value)
            guesses, is_all_done = optimization.next_step(f_guesses)
        settings_func(guesses)
        return guesses

    def _measure_opt_value_at_offset(self, set_offset_func, guess,
                                     target_value):
        set_offset_func(guess)
        mean_adc_value = self._get_mean_adc_value()
        logger.info("Alignment step (guess, mean): %d, %d" %
                     (guess, mean_adc_value))
        return abs(target_value - mean_adc_value)

    def _measure_opt_value_at_individual_settings(self, settings_func,
                                                  guesses, target_value):
        settings_func(guesses)
        msg = self.flush_and_get_measured_data_message()
        mean_adc_values = (msg.adc_ch1_pos.mean(), msg.adc_ch1_neg.mean(),
                           msg.adc_ch2_pos.mean(), msg.adc_ch2_neg.mean())
        logger.info("Alignment step (guesses, means):\n\t%s, %s" %
                     (guesses, [int(round(u)) for u in mean_adc_values]))
        return [abs(target_value - u) for u in mean_adc_values]

    def _set_full_scale(self, value):
        self.config.full_scale = value

    def _set_common_offset(self, value):
        self.config.common_offset = value

    def _set_individual_offsets(self, values):
        (self.config.channel1_offset_positive,
         self.config.channel1_offset_negative,
         self.config.channel2_offset_positive,
         self.config.channel2_offset_negative) = values

    def _set_individual_gains(self, values):
        (self.config.channel1_gain_positive,
         self.config.channel1_gain_negative,
         self.config.channel2_gain_positive,
         self.config.channel2_gain_negative) = values

    def _get_mean_adc_value(self):
        msg = self.flush_and_get_measured_data_message()
        mean_value = (msg.trace_ch1.mean() + msg.trace_ch2.mean()) / 2
        return mean_value

    def flush_and_get_measured_data_message(self):
        self.master.device.flushInput()
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
