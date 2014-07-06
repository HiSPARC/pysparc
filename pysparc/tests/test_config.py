import unittest
import logging

from mock import patch, sentinel, Mock, call

import pysparc.config


class ConfigTest(unittest.TestCase):
    def test_range(self):
        cfg = pysparc.config.NewConfig()
        low, high = self._get_range_from(cfg, 'ch1_voltage')
        self.assertEqual(low, 300)
        self.assertEqual(high, 1500)

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
