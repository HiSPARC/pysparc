import logging
import time

import bracket


logger = logging.getLogger(__name__)


class AlignADCs(object):
    def __init__(self, hardware):
        self.hardware = hardware
        self.config = hardware.config

    def align(self):
        # store original trigger condition
        original_trigger_condition = self.config.trigger_condition

        self._reset_config_for_alignment()
        self.config.trigger_condition = \
            self.config.build_trigger_condition(calibration_mode=True)
        target = 2048
        self._align_full_scale(target)
        self._align_common_offset(target)
        self._align_individual_offsets(target)
        target = 200
        self._align_full_scale(target)
        self._align_common_offset(target)
        self._align_individual_gains(target)

        # restore original trigger condition
        self.config.trigger_condition = original_trigger_condition

    def _reset_config_for_alignment(self):
        self._set_full_scale(0x80)
        self._set_common_offset(0x80)
        self._set_individual_offsets([0x80] * 4)

        self.hardware.flush_device()

    def _align_full_scale(self, target_value):
        logger.info("Aligning full scale")
        opt_value = self._align_offset(self._set_full_scale, target_value)
        logger.info("Full scale aligned (value): %d" % opt_value)

    def _align_common_offset(self, target_value):
        logger.info("Aligning common offset")
        opt_value = self._align_offset(self._set_common_offset,
                                       target_value)
        logger.info("Common offset aligned (value): %d" % opt_value)

    def _align_individual_offsets(self, target_value):
        logger.info("Aligning individual offsets")
        opt_values = self._align_individual_settings(
            self._set_individual_offsets, target_value)
        logger.info("Individual offsets aligned (values): %d %d %d %d" %
                    opt_values)

    def _align_individual_gains(self, target_value):
        logger.info("Aligning individual gains")
        opt_values = self._align_individual_settings(
            self._set_individual_gains, target_value)
        logger.info("Individual gains aligned (values): %d %d %d %d" %
                    opt_values)

    def _align_offset(self, set_offset_func, target_value):
        is_done = False

        a, b = 0, 0xff
        fa, fb = [self._measure_opt_value_at_offset(set_offset_func,
                                                    u, target_value)
                  for u in a, b]
        optimization = bracket.LinearInvertedIntegerRootFinder((a, b),
                                                               (fa, fb))
        guess = optimization.first_step()
        while not is_done:
            f_guess = self._measure_opt_value_at_offset(
                set_offset_func, guess, target_value)
            guess, is_done = optimization.next_step(f_guess)
        set_offset_func(guess)
        return guess

    def _align_individual_settings(self, settings_func, target_value):
        is_all_done = [False] * 4

        a, b = [0] * 4, [0xff] * 4
        fa, fb = [self._measure_opt_value_at_individual_settings(
            settings_func, u, target_value) for u in a, b]
        optimization = bracket.LinearParallelInvertedIntegerRootFinder(
            (a, b), (fa, fb))
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
        logger.debug("Alignment step (guess, mean): %d, %d" %
                     (guess, mean_adc_value))
        return target_value - mean_adc_value

    def _measure_opt_value_at_individual_settings(self, settings_func,
                                                  guesses, target_value):
        settings_func(guesses)
        msg = self.hardware.flush_and_get_measured_data_message()
        mean_adc_values = (msg.adc_ch1_pos.mean(), msg.adc_ch1_neg.mean(),
                           msg.adc_ch2_pos.mean(), msg.adc_ch2_neg.mean())
        logger.debug("Alignment step (guesses, means):\n\t%s, %s" %
                     (guesses, [int(round(u)) for u in mean_adc_values]))
        return [target_value - u for u in mean_adc_values]

    def _set_full_scale(self, value):
        self.config.full_scale = value

    def _set_common_offset(self, value):
        self.config.common_offset = value

    def _set_individual_offsets(self, values):
        (self.config.ch1_offset_positive,
         self.config.ch1_offset_negative,
         self.config.ch2_offset_positive,
         self.config.ch2_offset_negative) = values

    def _set_individual_gains(self, values):
        (self.config.ch1_gain_positive,
         self.config.ch1_gain_negative,
         self.config.ch2_gain_positive,
         self.config.ch2_gain_negative) = values

    def _get_mean_adc_value(self):
        msg = self.hardware.flush_and_get_measured_data_message()
        mean_value = (msg.trace_ch1.mean() + msg.trace_ch2.mean()) / 2
        return mean_value


class AlignADCsMasterSlave(AlignADCs):

    """Align a master and slave a the same time.

    Much of this class is implemented specifically for the master/slave
    combination. The overview of the alignment procedure, defined in the
    `:meth:align` method, is unchanged and only implemented in the parent
    class.

    """

    def __init__(self, master, slave):
        self.master = master
        self.master_config = master.config
        self.slave = slave
        self.slave_config = slave.config
        # The superclass knows of only one config.
        self.config = master.config

    def align(self):
        # store original trigger condition
        original_trigger_condition = self.master_config.trigger_condition

        self.master_config.trigger_condition = \
            self.config.build_trigger_condition(calibration_mode=True)
        self._reset_config_for_alignment()
        target = 2048
        self._align_full_scale(target)
        self._align_common_offset(target)
        self._align_individual_offsets(target)
        target = 200
        self._align_full_scale(target)
        self._align_common_offset(target)
        self._align_individual_gains(target)

        # restore original trigger condition
        self.config.trigger_condition = original_trigger_condition

    def _reset_config_for_alignment(self):
        self._set_full_scale(0x80, 0x80)
        self._set_common_offset(0x80, 0x80)
        self._set_individual_offsets([0x80] * 8)

        self.master.flush_device()
        self.slave.flush_device()

    def _align_full_scale(self, target_value):
        # synchronize
        self.master.flush_device()
        self.master.flush_and_get_measured_data_message()
        self.slave.flush_and_get_measured_data_message()
        self.master.flush_device()
        self.slave.flush_device()

        logger.info("Aligning full scale")
        opt_values = self._align_offset(self._set_full_scale, target_value)
        logger.info("Full scale aligned (value): %s" % str(opt_values))

    def _align_common_offset(self, target_value):
        logger.info("Aligning common offset")
        opt_value = self._align_offset(self._set_common_offset,
                                       target_value)
        logger.info("Common offset aligned (value): %s" % str(opt_value))

    def _align_individual_offsets(self, target_value):
        logger.info("Aligning individual offsets")
        opt_values = self._align_individual_settings(
            self._set_individual_offsets, target_value)
        logger.info("Individual offsets aligned (values): %s" %
                    str(opt_values))

    def _align_individual_gains(self, target_value):
        logger.info("Aligning individual gains")
        opt_values = self._align_individual_settings(
            self._set_individual_gains, target_value)
        logger.info("Individual gains aligned (values): %s" % str(opt_values))

    def _align_offset(self, set_offset_func, target_value):
        is_all_done = [False] * 2

        a, b = [0] * 2, [0xff] * 2
        fa, fb = [self._measure_opt_value_at_offset(set_offset_func,
                                                    u, target_value)
                  for u in a, b]
        optimization = bracket.LinearParallelInvertedIntegerRootFinder(
            (a, b), (fa, fb))
        guesses = optimization.first_step()
        while not sum(is_all_done) == 2:
            f_guesses = self._measure_opt_value_at_offset(
                set_offset_func, guesses, target_value)
            guesses, is_all_done = optimization.next_step(f_guesses)
        set_offset_func(*guesses)
        return guesses

    def _align_individual_settings(self, settings_func, target_value):
        is_all_done = [False] * 8

        a, b = [0] * 8, [0xff] * 8
        fa, fb = [self._measure_opt_value_at_individual_settings(
            settings_func, u, target_value) for u in a, b]
        optimization = bracket.LinearParallelInvertedIntegerRootFinder(
            (a, b), (fa, fb))
        guesses = optimization.first_step()
        while not sum(is_all_done) == 8:
            f_guesses = self._measure_opt_value_at_individual_settings(
                settings_func, guesses, target_value)
            guesses, is_all_done = optimization.next_step(f_guesses)
        settings_func(guesses)
        return guesses

    def _measure_opt_value_at_offset(self, set_offset_func, guesses,
                                     target_value):
        set_offset_func(*guesses)
        mean_adc_values = self._get_mean_adc_values()
        logger.debug("XY Alignment step (guesses, means):\n\t%s, %s" %
                     (guesses, [int(round(u)) for u in mean_adc_values]))
        return [target_value - u for u in mean_adc_values]

    def _measure_opt_value_at_individual_settings(self, settings_func,
                                                  guesses, target_value):
        settings_func(guesses)
        master, slave = self._flush_and_get_measured_data_messages()
        mean_adc_values = (master.adc_ch1_pos.mean(),
                           master.adc_ch1_neg.mean(),
                           master.adc_ch2_pos.mean(),
                           master.adc_ch2_neg.mean(),
                           slave.adc_ch1_pos.mean(),
                           slave.adc_ch1_neg.mean(),
                           slave.adc_ch2_pos.mean(),
                           slave.adc_ch2_neg.mean())
        logger.debug("Alignment step (guesses, means):\n\t%s, %s" %
                     (guesses, [int(round(u)) for u in mean_adc_values]))
        return [target_value - u for u in mean_adc_values]

    def _set_full_scale(self, master_value, slave_value):
        self.master_config.full_scale = master_value
        self.slave_config.full_scale = slave_value

    def _set_common_offset(self, master_value, slave_value):
        self.master_config.common_offset = master_value
        self.slave_config.common_offset = slave_value

    def _set_individual_offsets(self, values):
        (self.master_config.ch1_offset_positive,
         self.master_config.ch1_offset_negative,
         self.master_config.ch2_offset_positive,
         self.master_config.ch2_offset_negative,
         self.slave_config.ch1_offset_positive,
         self.slave_config.ch1_offset_negative,
         self.slave_config.ch2_offset_positive,
         self.slave_config.ch2_offset_negative) = values

    def _set_individual_gains(self, values):
        (self.master_config.ch1_gain_positive,
         self.master_config.ch1_gain_negative,
         self.master_config.ch2_gain_positive,
         self.master_config.ch2_gain_negative,
         self.slave_config.ch1_gain_positive,
         self.slave_config.ch1_gain_negative,
         self.slave_config.ch2_gain_positive,
         self.slave_config.ch2_gain_negative) = values

    def _get_mean_adc_values(self):
        master, slave = self._flush_and_get_measured_data_messages()
        master_mean_value = (master.trace_ch1.mean() +
                             master.trace_ch2.mean()) / 2
        slave_mean_value = (slave.trace_ch1.mean() +
                            slave.trace_ch2.mean()) / 2
        return master_mean_value, slave_mean_value

    def _flush_and_get_measured_data_messages(self):
        self.master.flush_device()
        self.slave.flush_device()
        master_msg = self.master.get_measured_data_message()
        slave_msg = self.slave.get_measured_data_message()
        logging.debug("Master: %s" % time.ctime(master_msg.timestamp))
        logging.debug("Slave: %s" % time.ctime(slave_msg.timestamp))
        return master_msg, slave_msg
