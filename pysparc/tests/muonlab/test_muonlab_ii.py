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

    @patch.object(muonlab_ii.MuonlabII, 'write_setting')
    def test_set_pmt1_voltage(self, mock_write):
        self.muonlab._set_pmt1_voltage(900)
        mock_write.assert_called_once_with('HV_1', 0x7f)


if __name__ == '__main__':
    unittest.main()
