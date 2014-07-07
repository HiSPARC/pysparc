import unittest
import logging

from mock import patch, sentinel, Mock, call

import pysparc.config


class ConfigTest(unittest.TestCase):

    def setUp(self):
        self.config = pysparc.config.NewConfig()

    def test_voltage_settings(self):
        for channel in [1, 2]:
            name = 'ch%d_voltage' % channel
            low, high = self._get_range_from(self.config, name)
            value = getattr(self.config, name)
            self.assertEqual(low, 300)
            self.assertEqual(high, 1500)
            self.assertEqual(value, low)

    def test_threshold_settings(self):
        for channel in [1, 2]:
            for level in ['low', 'high']:
                name = 'ch%d_threshold_%s' % (channel, level)
                low, high = self._get_range_from(self.config, name)
                value = getattr(self.config, name)
                self.assertEqual(low, 0)
                self.assertEqual(high, 2000)
                self.assertEqual(value, 30 if level == 'low' else 70)

    def test_individual_gains_and_offsets(self):
        for channel in [1, 2]:
            for type in ['gain', 'offset']:
                for edge in ['positive', 'negative']:
                    name = 'ch%d_%s_%s' % (channel, type, edge)
                    low, high = self._get_range_from(self.config, name)
                    value = getattr(self.config, name)
                    self.assertEqual(low, 0x00)
                    self.assertEqual(high, 0xff)
                    self.assertEqual(value, 0x80)

    def test_common_gain_and_offset(self):
        # Unfortunately, the common gain is called 'full scale'
        for name in ['common_offset', 'full_scale']:
            low, high = self._get_range_from(self.config, name)
            value = getattr(self.config, name)
            self.assertEqual(low, 0x00)
            self.assertEqual(high, 0xff)
            self.assertEqual(value, 0x00)

    def _get_range_from(self, instance, name):
        """Get the range from an atom object.

        :param instance: instance of an Atom class
        :param name: name of the range attribute

        :returns: (low, high) values of the range

        """
        atom = instance.get_member(name)
        validator, (low, high) = atom.validate_mode
        return low, high


if __name__ == '__main__':
    unittest.main()
