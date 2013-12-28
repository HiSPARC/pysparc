import unittest

from mock import patch

from pysparc.muonlab import muonlab_ii


class MuonlabIITest(unittest.TestCase):

    @patch('pysparc.muonlab.muonlab_ii.pylibftdi.Device')
    def setUp(self, mock_Device):
        self.mock_Device = mock_Device
        self.muonlab = muonlab_ii.MuonlabII()

    def test_address_is_dictionary(self):
        self.assertIsInstance(self.muonlab._address, dict)

    def test_address_values(self):
        # Yes, really, HV1 and 2 are reversed
        self.assertEqual(self.muonlab._address['HV_1'], 2)
        self.assertEqual(self.muonlab._address['HV_2'], 1)
        self.assertEqual(self.muonlab._address['THR_1'], 3)
        self.assertEqual(self.muonlab._address['THR_2'], 4)
        self.assertEqual(self.muonlab._address['MEAS'], 5)

    def test_init_opens_device_with_description(self):
        self.mock_Device.assert_called_once_with('USB <-> Serial')

    def test_init_saves_device_as_attribute(self):
        self.assertIs(self.muonlab._device, self.mock_Device.return_value)

    def test_write_setting_raises_unknown_setting(self):
        self.assertRaises(TypeError, self.muonlab.write_setting,
                          'UNKNOWN', 'foo')

    def test_write_setting_writes_correct_data(self):
        self.muonlab.write_setting('HV_1', 0b10100101)
        self.muonlab._device.write.assert_called_with(
            chr(0b10101010) + chr(0b00100101))

    def test_write_setting_writes_only_one_byte_for_measurement(self):
        self.muonlab.write_setting('MEAS', 0b10100101)
        self.muonlab._device.write.assert_called_with(chr(0b01010101))

    @patch.object(muonlab_ii.MuonlabII, 'write_setting')
    def test_set_pmt1_voltage_calls_write_setting(self, mock_write):
        self.muonlab._set_pmt1_voltage(900)
        mock_write.assert_called_once_with('HV_1', 0x7f)
        self.muonlab._set_pmt1_voltage(600)
        mock_write.assert_called_with('HV_1', 0x3f)

    @patch.object(muonlab_ii.MuonlabII, 'write_setting')
    @patch.object(muonlab_ii, 'map_setting')
    def test_set_pmt1_voltage_calls_map_setting(self, mock_map,
                                                mock_write):
        self.muonlab._set_pmt1_voltage(900)
        mock_map.assert_called_once_with(900, 300, 1500, 0x00, 0xff)

    @patch.object(muonlab_ii.MuonlabII, 'write_setting')
    def test_set_pmt2_voltage_calls_write_setting(self, mock_write):
        self.muonlab._set_pmt2_voltage(900)
        mock_write.assert_called_once_with('HV_2', 0x7f)
        self.muonlab._set_pmt2_voltage(600)
        mock_write.assert_called_with('HV_2', 0x3f)

    @patch.object(muonlab_ii.MuonlabII, 'write_setting')
    @patch.object(muonlab_ii, 'map_setting')
    def test_set_pmt2_voltage_calls_map_setting(self, mock_map,
                                                mock_write):
        self.muonlab._set_pmt2_voltage(900)
        mock_map.assert_called_once_with(900, 300, 1500, 0x00, 0xff)

    @patch.object(muonlab_ii.MuonlabII, 'write_setting')
    def test_set_pmt1_threshold_calls_write_setting(self, mock_write):
        self.muonlab._set_pmt1_threshold(600)
        mock_write.assert_called_with('THR_1', 0x7f)
        self.muonlab._set_pmt1_threshold(300)
        mock_write.assert_called_with('THR_1', 0x3f)

    @patch.object(muonlab_ii.MuonlabII, 'write_setting')
    @patch.object(muonlab_ii, 'map_setting')
    def test_set_pmt1_threshold_calls_map_setting(self, mock_map,
                                                  mock_write):
        self.muonlab._set_pmt1_threshold(600)
        mock_map.assert_called_once_with(600, 0, 1200, 0x00, 0xff)

    @patch.object(muonlab_ii.MuonlabII, 'write_setting')
    def test_set_pmt2_threshold_calls_write_setting(self, mock_write):
        self.muonlab._set_pmt2_threshold(600)
        mock_write.assert_called_with('THR_2', 0x7f)
        self.muonlab._set_pmt2_threshold(300)
        mock_write.assert_called_with('THR_2', 0x3f)

    @patch.object(muonlab_ii.MuonlabII, 'write_setting')
    @patch.object(muonlab_ii, 'map_setting')
    def test_set_pmt2_threshold_calls_map_setting(self, mock_map,
                                                  mock_write):
        self.muonlab._set_pmt2_threshold(600)
        mock_map.assert_called_once_with(600, 0, 1200, 0x00, 0xff)

    @patch.object(muonlab_ii.MuonlabII, 'write_setting')
    def test_set_lifetime_measurement(self, mock_write):
        self.muonlab._set_lifetime_measurement()
        mock_write.assert_called_with('MEAS', 0xff)

    @patch.object(muonlab_ii.MuonlabII, 'write_setting')
    def test_set_coincidence_measurement(self, mock_write):
        self.muonlab._set_coincidence_measurement()
        mock_write.assert_called_with('MEAS', 0x00)

    def test_read_lifetime_data_returns_list(self):
        self.muonlab._device.read.return_value = ''
        data = self.muonlab.read_lifetime_data()
        self.assertIsInstance(data, list)

        self.muonlab._device.read.return_value = '\x85\x20'
        data = self.muonlab.read_lifetime_data()
        self.assertIsInstance(data, list)

    @patch.object(muonlab_ii, 'READ_SIZE')
    def test_read_lifetime_data_calls_device_read(self, mock_size):
        self.muonlab._device.read.return_value = ''
        self.muonlab.read_lifetime_data()
        self.muonlab._device.read.assert_called_once_with(mock_size)

    def test_READ_SIZE_is_multiple_of_62(self):
        self.assertTrue(muonlab_ii.READ_SIZE % 62 == 0)

    def test_read_lifetime_data_acceptance(self):
        self.muonlab._device.read.return_value = ''
        data = self.muonlab.read_lifetime_data()
        self.assertEqual(data, [])

        self.muonlab._device.read.return_value = '\x85\x20'
        data = self.muonlab.read_lifetime_data()
        self.assertEqual(data, [2200.])

        self.muonlab._device.read.return_value = '\x85\x20\x80\x13'
        data = self.muonlab.read_lifetime_data()
        self.assertEqual(data, [2200., 118.75])

    def test_read_lifetime_data_raises_ValueError(self):
        self.muonlab._device.read.return_value = '\x00\x00'
        self.assertRaises(ValueError, self.muonlab.read_lifetime_data)

        self.muonlab._device.read.return_value = '\x80\x80'
        self.assertRaises(ValueError, self.muonlab.read_lifetime_data)


if __name__ == '__main__':
    unittest.main()
