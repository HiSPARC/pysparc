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

        self.config.trigger_condition = \
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


class AlignADCsPrimarySecondary(AlignADCs):

    """Align a primary and secondary a the same time.

    Much of this class is implemented specifically for the primary/secondary
    combination. The overview of the alignment procedure, defined in the
    `:meth:align` method, is unchanged and only implemented in the parent
    class.

    """

    def __init__(self, primary, secondary):
        self.primary = primary
        self.primary_config = primary.config
        self.secondary = secondary
        self.secondary_config = secondary.config
        # The superclass knows of only one config.
        self.config = primary.config

    def _reset_config_for_alignment(self):
        self._set_full_scale(0x80, 0x80)
        self._set_common_offset(0x80, 0x80)
        self._set_individual_offsets([0x80] * 8)

        # Synchronize primary and secondary.
        # Step 1. Flush old messages
        self.primary.flush_device()
        self.secondary.flush_device()
        # Step 2. Make sure both primary and secondary are sending messages
        self.primary.flush_and_get_measured_data_message()
        self.secondary.flush_and_get_measured_data_message()
        # Step 3. Flush both devices
        self.primary.flush_device()
        self.secondary.flush_device()

    def _align_full_scale(self, target_value):
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
        logger.debug("Alignment step (guesses, means):\n\t%s, %s" %
                     (guesses, [int(round(u)) for u in mean_adc_values]))
        return [target_value - u for u in mean_adc_values]

    def _measure_opt_value_at_individual_settings(self, settings_func,
                                                  guesses, target_value):
        settings_func(guesses)
        primary, secondary = self._flush_and_get_measured_data_messages()
        mean_adc_values = (primary.adc_ch1_pos.mean(),
                           primary.adc_ch1_neg.mean(),
                           primary.adc_ch2_pos.mean(),
                           primary.adc_ch2_neg.mean(),
                           secondary.adc_ch1_pos.mean(),
                           secondary.adc_ch1_neg.mean(),
                           secondary.adc_ch2_pos.mean(),
                           secondary.adc_ch2_neg.mean())
        logger.debug("Alignment step (guesses, means):\n\t%s, %s" %
                     (guesses, [int(round(u)) for u in mean_adc_values]))
        return [target_value - u for u in mean_adc_values]

    def _set_full_scale(self, primary_value, secondary_value):
        self.primary_config.full_scale = primary_value
        self.secondary_config.full_scale = secondary_value

    def _set_common_offset(self, primary_value, secondary_value):
        self.primary_config.common_offset = primary_value
        self.secondary_config.common_offset = secondary_value

    def _set_individual_offsets(self, values):
        (self.primary_config.ch1_offset_positive,
         self.primary_config.ch1_offset_negative,
         self.primary_config.ch2_offset_positive,
         self.primary_config.ch2_offset_negative,
         self.secondary_config.ch1_offset_positive,
         self.secondary_config.ch1_offset_negative,
         self.secondary_config.ch2_offset_positive,
         self.secondary_config.ch2_offset_negative) = values

    def _set_individual_gains(self, values):
        (self.primary_config.ch1_gain_positive,
         self.primary_config.ch1_gain_negative,
         self.primary_config.ch2_gain_positive,
         self.primary_config.ch2_gain_negative,
         self.secondary_config.ch1_gain_positive,
         self.secondary_config.ch1_gain_negative,
         self.secondary_config.ch2_gain_positive,
         self.secondary_config.ch2_gain_negative) = values

    def _get_mean_adc_values(self):
        primary, secondary = self._flush_and_get_measured_data_messages()
        primary_mean_value = (primary.trace_ch1.mean() +
                             primary.trace_ch2.mean()) / 2
        secondary_mean_value = (secondary.trace_ch1.mean() +
                            secondary.trace_ch2.mean()) / 2
        return primary_mean_value, secondary_mean_value

    def _flush_and_get_measured_data_messages(self):
        self.primary.flush_device()
        self.secondary.flush_device()
        primary_msg = self.primary.get_measured_data_message()
        secondary_msg = self.secondary.get_measured_data_message()
        logging.debug("Primary: %s" % time.ctime(primary_msg.timestamp))
        logging.debug("Secondary: %s" % time.ctime(secondary_msg.timestamp))
        return primary_msg, secondary_msg
