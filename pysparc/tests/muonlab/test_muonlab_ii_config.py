import unittest

from mock import sentinel, Mock

from pysparc.muonlab import muonlab_ii


class MuonlabIIConfigTest(unittest.TestCase):

    def setUp(self):
        self.mock_muonlab = Mock()
        self.muonlab_config = muonlab_ii.MuonlabIIConfig(self.mock_muonlab)

    def test_muonlab_config_init_sets_hardware(self):
        self.assertIs(self.muonlab_config._hardware, self.mock_muonlab)

    def test_muonlab_config_has_config_attributes(self):
        self.assertTrue(hasattr(self.muonlab_config, 'pmt1_voltage'))
        self.assertTrue(hasattr(self.muonlab_config, 'pmt2_voltage'))
        self.assertTrue(hasattr(self.muonlab_config, 'pmt1_threshold'))
        self.assertTrue(hasattr(self.muonlab_config, 'pmt2_threshold'))
        self.assertTrue(hasattr(self.muonlab_config, 'mode'))

    def test_muonlab_config_inits_low_voltages(self):
        self.assertEqual(self.muonlab_config.pmt1_voltage, 300)
        self.assertEqual(self.muonlab_config.pmt2_voltage, 300)

    def test_muonlab_config_sets_config_attributes(self):
        self.muonlab_config.pmt1_voltage = sentinel.V1
        self.assertEqual(self.muonlab_config.pmt1_voltage, sentinel.V1)
        self.muonlab_config.pmt2_voltage = sentinel.V2
        self.assertEqual(self.muonlab_config.pmt2_voltage, sentinel.V2)

        self.muonlab_config.pmt1_threshold = sentinel.THR1
        self.assertEqual(self.muonlab_config.pmt1_threshold, sentinel.THR1)
        self.muonlab_config.pmt2_threshold = sentinel.THR2
        self.assertEqual(self.muonlab_config.pmt2_threshold, sentinel.THR2)

        self.muonlab_config.mode = 'lifetime'
        self.assertEqual(self.muonlab_config.mode, 'lifetime')

    def test_muonlab_config_set_voltage_sets_device_voltage(self):
        self.mock_muonlab.reset_mock()

        self.muonlab_config.pmt1_voltage = sentinel.V1
        self.mock_muonlab._set_pmt1_voltage.assert_called_once_with(
            sentinel.V1)
        self.muonlab_config.pmt2_voltage = sentinel.V2
        self.mock_muonlab._set_pmt2_voltage.assert_called_once_with(
            sentinel.V2)

    def test_muonlab_config_set_voltage_sets_device_thresholds(self):
        self.mock_muonlab.reset_mock()

        self.muonlab_config.pmt1_threshold = sentinel.THR1
        self.mock_muonlab._set_pmt1_threshold.assert_called_once_with(
            sentinel.THR1)
        self.muonlab_config.pmt2_threshold = sentinel.THR2
        self.mock_muonlab._set_pmt2_threshold.assert_called_once_with(
            sentinel.THR2)

    def test_muonlab_config_set_mode_sets_device_mode(self):
        self.mock_muonlab.reset_mock()

        self.muonlab_config.mode = 'lifetime'
        self.mock_muonlab._set_lifetime_measurement.assert_called_once_with()

        self.muonlab_config.mode = 'coincidence'
        self.mock_muonlab._set_coincidence_measurement.assert_called_once_with()

    def test_muonlab_config_set_mode_raises_valueerror(self):
        with self.assertRaises(ValueError):
            self.muonlab_config.mode = 'unknown'

    def test_muonlab_config_init_sets_device_parameters(self):
        self.mock_muonlab._set_pmt1_voltage.assert_called_once_with(300)
        self.mock_muonlab._set_pmt2_voltage.assert_called_once_with(300)
        self.mock_muonlab._set_pmt1_threshold.assert_called_once_with(0)
        self.mock_muonlab._set_pmt2_threshold.assert_called_once_with(0)
        self.mock_muonlab._set_lifetime_measurement.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
