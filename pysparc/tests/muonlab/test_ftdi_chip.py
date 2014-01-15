import unittest

from mock import patch, sentinel

from pysparc.muonlab import ftdi_chip


class FtdiChipStaticMethodTest(unittest.TestCase):

    def test_list_devices_returns_list(self):
        devices = ftdi_chip.FtdiChip.find_all()
        self.assertIsInstance(devices, list)

    @patch('pysparc.muonlab.ftdi_chip.pylibftdi.Driver')
    def test_list_devices_returns_devices(self, mock_driver):
        fake_device_list = sentinel.device_list
        mock_driver.return_value.list_devices.return_value = \
            fake_device_list
        devices = ftdi_chip.FtdiChip.find_all()
        self.assertIs(devices, sentinel.device_list)


class FtdiChipTest(unittest.TestCase):

    @patch('pysparc.muonlab.ftdi_chip.pylibftdi.Device')
    def setUp(self, mock_Device):
        self.mock_device = mock_Device.return_value
        self.device = ftdi_chip.FtdiChip()

    @patch('pysparc.muonlab.ftdi_chip.pylibftdi.Device')
    def test_init_opens_device_with_description(self, mock_Device):
        device = ftdi_chip.FtdiChip(sentinel.description)
        mock_Device.assert_called_once_with(sentinel.description)

    def test_init_stores_device(self):
        self.assertIs(self.device._device, self.mock_device)

    @patch('pysparc.muonlab.ftdi_chip.pylibftdi.Device')
    def test_init_raises_DeviceNotFoundError_if_not_present(self,
                                                            mock_Device):
        mock_Device.side_effect = ftdi_chip.pylibftdi.FtdiError(
            "FtdiError: device not found (-3)")
        self.assertRaises(ftdi_chip.DeviceNotFoundError,
                          ftdi_chip.FtdiChip)

    @patch('pysparc.muonlab.ftdi_chip.pylibftdi.Device')
    def test_init_raises_DeviceNotFoundError_if_no_rights(self,
                                                          mock_Device):
        # This occurs on OS X Mavericks.  You'll have to unload the driver
        # from OS X:
        # $ sudo kextunload -b com.apple.driver.AppleUSBFTDI
        mock_Device.side_effect = ftdi_chip.pylibftdi.FtdiError(
            "unable to claim usb device. Make sure the default FTDI driver is not in use (-5)")
        self.assertRaises(ftdi_chip.DeviceNotFoundError,
                          ftdi_chip.FtdiChip)


if __name__ == '__main__':
    unittest.main()
