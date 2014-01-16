import unittest

from mock import patch

from pysparc.muonlab import muonlab_ii


class MuonlabIITest(unittest.TestCase):

    @patch('pysparc.muonlab.muonlab_ii.FtdiChip')
    def setUp(self, mock_Device):
        self.mock_Device = mock_Device
        self.mock_device = mock_Device.return_value
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
        self.assertIs(self.muonlab._device, self.mock_device)

    def test_write_setting_raises_unknown_setting(self):
        self.assertRaises(TypeError, self.muonlab._write_setting,
                          'UNKNOWN', 'foo')

    def test_write_setting_writes_correct_data(self):
        self.muonlab._write_setting('HV_1', 0b10100101)
        self.muonlab._device.write.assert_called_with(
            chr(0b10101010) + chr(0b00100101))

    def test_write_setting_writes_only_one_byte_for_measurement(self):
        self.muonlab._write_setting('MEAS', 0b10100101)
        self.muonlab._device.write.assert_called_with(chr(0b01010101))

    @patch.object(muonlab_ii.MuonlabII, '_write_setting')
    def test_set_pmt1_voltage_calls_write_setting(self, mock_write):
        self.muonlab.set_pmt1_voltage(900)
        mock_write.assert_called_once_with('HV_1', 0x7f)
        self.muonlab.set_pmt1_voltage(600)
        mock_write.assert_called_with('HV_1', 0x3f)

    @patch.object(muonlab_ii.MuonlabII, '_write_setting')
    @patch.object(muonlab_ii, 'map_setting')
    def test_set_pmt1_voltage_calls_map_setting(self, mock_map,
                                                mock_write):
        self.muonlab.set_pmt1_voltage(900)
        mock_map.assert_called_once_with(900, 300, 1500, 0x00, 0xff)

    @patch.object(muonlab_ii.MuonlabII, '_write_setting')
    def test_set_pmt2_voltage_calls_write_setting(self, mock_write):
        self.muonlab.set_pmt2_voltage(900)
        mock_write.assert_called_once_with('HV_2', 0x7f)
        self.muonlab.set_pmt2_voltage(600)
        mock_write.assert_called_with('HV_2', 0x3f)

    @patch.object(muonlab_ii.MuonlabII, '_write_setting')
    @patch.object(muonlab_ii, 'map_setting')
    def test_set_pmt2_voltage_calls_map_setting(self, mock_map,
                                                mock_write):
        self.muonlab.set_pmt2_voltage(900)
        mock_map.assert_called_once_with(900, 300, 1500, 0x00, 0xff)

    @patch.object(muonlab_ii.MuonlabII, '_write_setting')
    def test_set_pmt1_threshold_calls_write_setting(self, mock_write):
        self.muonlab.set_pmt1_threshold(600)
        mock_write.assert_called_with('THR_1', 0x7f)
        self.muonlab.set_pmt1_threshold(300)
        mock_write.assert_called_with('THR_1', 0x3f)

    @patch.object(muonlab_ii.MuonlabII, '_write_setting')
    @patch.object(muonlab_ii, 'map_setting')
    def test_set_pmt1_threshold_calls_map_setting(self, mock_map,
                                                  mock_write):
        self.muonlab.set_pmt1_threshold(600)
        mock_map.assert_called_once_with(600, 0, 1200, 0x00, 0xff)

    @patch.object(muonlab_ii.MuonlabII, '_write_setting')
    def test_set_pmt2_threshold_calls_write_setting(self, mock_write):
        self.muonlab.set_pmt2_threshold(600)
        mock_write.assert_called_with('THR_2', 0x7f)
        self.muonlab.set_pmt2_threshold(300)
        mock_write.assert_called_with('THR_2', 0x3f)

    @patch.object(muonlab_ii.MuonlabII, '_write_setting')
    @patch.object(muonlab_ii, 'map_setting')
    def test_set_pmt2_threshold_calls_map_setting(self, mock_map,
                                                  mock_write):
        self.muonlab.set_pmt2_threshold(600)
        mock_map.assert_called_once_with(600, 0, 1200, 0x00, 0xff)

    @patch.object(muonlab_ii.MuonlabII, '_write_setting')
    def test_select_lifetime_measurement(self, mock_write):
        self.muonlab.select_lifetime_measurement()
        mock_write.assert_called_with('MEAS', 0xff)

    @patch.object(muonlab_ii.MuonlabII, '_write_setting')
    def test_select_coincidence_measurement(self, mock_write):
        self.muonlab.select_coincidence_measurement()
        mock_write.assert_called_with('MEAS', 0x00)

    def test_read_lifetime_data_returns_list(self):
        self.muonlab._device.read.return_value = ''
        data = self.muonlab.read_lifetime_data()
        self.assertIsInstance(data, list)

        self.muonlab._device.read.return_value = '\x85\x20'
        data = self.muonlab.read_lifetime_data()
        self.assertIsInstance(data, list)

    def test_read_lifetime_data_calls_device_read(self):
        self.muonlab._device.read.return_value = ''
        self.muonlab.read_lifetime_data()
        self.muonlab._device.read.assert_called_once_with()

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
        # first received byte is not high byte
        self.muonlab._device.read.return_value = '\x00\x00'
        self.assertRaises(ValueError, self.muonlab.read_lifetime_data)

        # second received byte is not low byte
        self.muonlab._device.read.return_value = '\x80\x80'
        self.assertRaises(ValueError, self.muonlab.read_lifetime_data)

    def test_read_coincidence_data_returns_list(self):
        self.muonlab._device.read.return_value = ''
        data = self.muonlab.read_coincidence_data()
        self.assertIsInstance(data, list)

        self.muonlab._device.read.return_value = '\xc5\x20'
        data = self.muonlab.read_coincidence_data()
        self.assertIsInstance(data, list)

    def test_read_coincidence_data_calls_device_read(self):
        self.muonlab._device.read.return_value = ''
        self.muonlab.read_coincidence_data()
        self.muonlab._device.read.assert_called_once_with()

    def test_read_coincidence_data_returns_time_and_flags(self):
        self.muonlab._device.read.return_value = '\xc0\x00'
        data = self.muonlab.read_coincidence_data()
        self.assertEqual(data, [(0., True, False)])

        self.muonlab._device.read.return_value = '\x80\x40'
        data = self.muonlab.read_coincidence_data()
        self.assertEqual(data, [(0., False, True)])

        self.muonlab._device.read.return_value = '\xc0\x40'
        data = self.muonlab.read_coincidence_data()
        self.assertEqual(data, [(0., True, True)])

    def test_read_coincidence_data_returns_positive_time_if_both_hit(self):
        self.muonlab._device.read.return_value = '\xc0\x41'
        data = self.muonlab.read_coincidence_data()
        self.assertEqual(data, [(6.25 / 12, True, True)])

    def test_read_coincidence_data_acceptance(self):
        self.muonlab._device.read.return_value = ''
        data = self.muonlab.read_coincidence_data()
        self.assertEqual(data, [])

        self.muonlab._device.read.return_value = '\xc5\x20'
        data = self.muonlab.read_coincidence_data()
        self.assertEqual(data, [(183.33333333333334, True, False)])

        self.muonlab._device.read.return_value = '\xc5\x20\xc0\x13'
        data = self.muonlab.read_coincidence_data()
        self.assertEqual(data, [(183.33333333333334, True, False), 
                                (9.895833333333334, True, False)])

        self.muonlab._device.read.return_value = '\x85\x60'
        data = self.muonlab.read_coincidence_data()
        self.assertEqual(data, [(-183.33333333333334, False, True)])

        self.muonlab._device.read.return_value = '\x85\x60\x80\x53'
        data = self.muonlab.read_coincidence_data()
        self.assertEqual(data, [(-183.33333333333334, False, True),
                                (-9.895833333333334, False, True)])

    def test_read_coincidence_data_raises_ValueError(self):
        # first received byte is not high byte
        self.muonlab._device.read.return_value = '\x00\x00'
        self.assertRaises(ValueError, self.muonlab.read_coincidence_data)

        # second received byte is not low byte
        self.muonlab._device.read.return_value = '\x80\x80'
        self.assertRaises(ValueError, self.muonlab.read_coincidence_data)

        # no detector has 'hit first' flag set
        self.muonlab._device.read.return_value = '\x80\x00'
        self.assertRaises(ValueError, self.muonlab.read_coincidence_data)

    @patch.object(muonlab_ii.MuonlabII, 'set_pmt1_voltage')
    @patch.object(muonlab_ii.MuonlabII, 'set_pmt2_voltage')
    def test_destructor_resets_voltages(self, mock_pmt2_hv, mock_pmt1_hv):
        del self.muonlab
        mock_pmt1_hv.assert_called_once_with(0)
        mock_pmt2_hv.assert_called_once_with(0)

    def test_destructor_closes_device(self):
        del self.muonlab
        self.mock_device.close.assert_called_once_with()

    def test_flush_device_calls_device_flush(self):
        self.muonlab.flush_device()
        self.mock_device.flush_device.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
