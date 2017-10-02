import logging

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

        self._do_alignment()

        # restore original trigger condition
        self.config.trigger_condition = original_trigger_condition

    def align_slave(self, master):
        # store original trigger condition
        original_trigger_condition = master.config.trigger_condition

        self._reset_config_for_alignment()
        master.config.trigger_condition = \
            master.config.build_trigger_condition(calibration_mode=True)

        self._do_alignment()

        # restore original trigger condition
        master.config.trigger_condition = original_trigger_condition

    def _do_alignment(self):
        target = 2048
        self._align_full_scale(target)
        self._align_common_offset(target)
        self._align_individual_offsets(target)
        target = 200
        self._align_full_scale(target)
        self._align_common_offset(target)
        self._align_individual_gains(target)

    def _reset_config_for_alignment(self):
        self._set_full_scale(0x80)
        self._set_common_offset(0x80)
        self._set_individual_offsets([0x80] * 4)

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
