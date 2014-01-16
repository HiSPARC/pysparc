import unittest
import logging

from mock import patch, sentinel, Mock

from pysparc.muonlab import ftdi_chip


logging.disable(logging.CRITICAL)


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
    def test_init_raises_DeviceError_if_no_rights(self, mock_Device):
        # This occurs on OS X Mavericks.  You'll have to unload the driver
        # from OS X:
        # $ sudo kextunload -b com.apple.driver.AppleUSBFTDI
        mock_Device.side_effect = ftdi_chip.pylibftdi.FtdiError(
            "unable to claim usb device. Make sure the default FTDI driver is not in use (-5)")
        self.assertRaises(ftdi_chip.DeviceError,
                          ftdi_chip.FtdiChip)

    @patch('pysparc.muonlab.ftdi_chip.pylibftdi.Device')
    def test_init_raises_DeviceError_if_error_and_returns_ftdi_msg(self,
        mock_Device):

        msg = "Foobaz"
        mock_Device.side_effect = ftdi_chip.pylibftdi.FtdiError(msg)
        self.assertRaisesRegexp(ftdi_chip.DeviceError, msg,
                          ftdi_chip.FtdiChip)

    @patch('pysparc.muonlab.ftdi_chip.pylibftdi.Device')
    @patch.object(ftdi_chip.FtdiChip, 'flush_device')
    def test_init_calls_flush_device(self, mock_flush, mock_Device):
        ftdi_chip.FtdiChip()
        mock_flush.assert_called_once_with()

    def test_flush_device_flushes_device(self):
        self.mock_device.flush.assert_called_once_with()

    def test_BUFFER_SIZE_is_multiple_of_62(self):
        self.assertTrue(ftdi_chip.BUFFER_SIZE % 62 == 0)

    @patch.object(ftdi_chip, 'BUFFER_SIZE')
    def test_flush_device(self, mock_size):
        self.mock_device.reset_mock()
        self.device.flush_device()

        self.mock_device.flush.assert_called_once_with()
        self.mock_device.read.assert_called_once_with(mock_size)
        method_names = [x[0] for x in self.mock_device.method_calls]
        # Assert flush called before read
        self.assertLess(method_names.index('flush'),
                        method_names.index('read'))

    def test_close_closes_device(self):
        self.device.close()
        self.mock_device.close.assert_called_once_with()

    def test_destructor_calls_close(self):
        mock_close = Mock()
        self.device.close = mock_close
        del self.device
        mock_close.assert_called_once_with()

    def test_READ_SIZE_is_multiple_of_62(self):
        self.assertTrue(ftdi_chip.READ_SIZE % 62 == 0)

    @patch.object(ftdi_chip, 'READ_SIZE')
    def test_read_calls_device_read_with_correct_size(self, mock_size):
        self.mock_device.reset_mock()
        self.device.read()
        self.mock_device.read.assert_called_once_with(mock_size)

    def test_read_returns_device_read(self):
        data = self.device.read()
        self.assertIs(data, self.mock_device.read.return_value)

    def test_read_raises_ReadError_on_failed_read(self):
        self.mock_device.read.side_effect = \
            ftdi_chip.pylibftdi.FtdiError("Foo")
        self.assertRaisesRegexp(ftdi_chip.ReadError, "Foo",
                                self.device.read)

    def test_read_retries_read_on_exception_three_times(self):
        self.mock_device.read.side_effect = [
            ftdi_chip.pylibftdi.FtdiError(),
            ftdi_chip.pylibftdi.FtdiError(), None]
        self.device.read()

    def test_write_calls_device_write(self):
        self.device.write(sentinel.data)
        self.mock_device.write.assert_called_once_with(sentinel.data)

    def test_write_retries_write_on_exception_three_times(self):
        self.mock_device.write.side_effect = [
            ftdi_chip.pylibftdi.FtdiError(),
            ftdi_chip.pylibftdi.FtdiError(), None]
        self.device.write(sentinel.data)

    def test_write_raises_WriteError_on_failed_write(self):
        self.mock_device.write.side_effect = \
            ftdi_chip.pylibftdi.FtdiError("Foo")
        self.assertRaisesRegexp(ftdi_chip.WriteError, "Foo",
                                self.device.write, sentinel.data)


if __name__ == '__main__':
    unittest.main()
