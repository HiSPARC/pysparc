import unittest
import logging

from mock import patch, sentinel, Mock, call

from pysparc import ftdi_chip


logging.disable(logging.CRITICAL)


class FtdiChipStaticMethodTest(unittest.TestCase):

    def test_list_devices_returns_list(self):
        devices = ftdi_chip.FtdiChip.find_all()
        self.assertIsInstance(devices, list)

    @patch('pysparc.ftdi_chip.pylibftdi.Driver')
    def test_list_devices_returns_devices(self, mock_driver):
        fake_device_list = sentinel.device_list
        mock_driver.return_value.list_devices.return_value = \
            fake_device_list
        devices = ftdi_chip.FtdiChip.find_all()
        self.assertIs(devices, sentinel.device_list)


class FtdiChipTest(unittest.TestCase):

    @patch('pysparc.ftdi_chip.pylibftdi.Device')
    def setUp(self, mock_Device):
        self.device = ftdi_chip.FtdiChip()
        # this setup does not depend on __init__ to store the device.  We
        # do that explicitly here, to isolate quite a few tests from
        # correct __init__ behavior.  Be sure to test __init__!  We also
        # do *not* use mock_Device.return_value as the mock_device.  This
        # is to ensure we have a clean, not-even-called-once mock for
        # use in the tests.  This saves us a few reset_mock().
        self.mock_device = Mock()
        self.device._device = self.mock_device

    @patch('pysparc.ftdi_chip.pylibftdi.Device')
    def test_init_stores_device_description(self, mock_Device):
        device = ftdi_chip.FtdiChip(sentinel.description)
        self.assertIs(device._device_description, sentinel.description)

    @patch.object(ftdi_chip.FtdiChip, 'open')
    def test_init_calls_open(self, mock_open):
        device = ftdi_chip.FtdiChip()
        mock_open.assert_called_once_with()

    def test_set_line_settings(self):
        self.device.set_line_settings(sentinel.bits, sentinel.parity,
                                      sentinel.stop_bit)
        self.mock_device.ftdi_fn.ftdi_set_line_property.assert_called_once_with(
            sentinel.bits, sentinel.stop_bit, sentinel.parity)

    def test_flush_flushes_device(self):
        self.device.flush()
        self.mock_device.flush.assert_called_once_with()

    def test_BUFFER_SIZE_is_multiple_of_62(self):
        self.assertTrue(ftdi_chip.BUFFER_SIZE % 62 == 0)

    @patch.object(ftdi_chip, 'BUFFER_SIZE')
    def test_flush(self, mock_size):
        mock = Mock()
        self.device._device = mock.device
        self.device.read = mock.read

        self.device.flush()

        expected = [call.device.flush(), call.read(mock_size)]
        self.assertListEqual(expected, mock.mock_calls)

    def test_close_closes_device(self):
        self.device.close()
        self.mock_device.close.assert_called_once_with()

    def test_close_sets_closed(self):
        self.device.close()
        self.assertTrue(self.device.closed)

    def test_close_only_closes_if_not_closed(self):
        self.device.close()
        try:
            self.device.close()
        except AttributeError:
            self.fail("close() raises AtributeError")
        else:
            self.mock_device.close.assert_called_once_with()

    def test_close_sets_device_to_none(self):
        self.device.close()
        self.assertIs(self.device._device, None)

    def test_destructor_calls_close(self):
        mock_close = Mock()
        self.device.close = mock_close
        del self.device
        mock_close.assert_called_once_with()

    @patch.object(ftdi_chip.FtdiChip, 'close')
    def test_read_closes_device_if_exception(self, mock_close):
        self.mock_device.read.side_effect = \
            ftdi_chip.pylibftdi.FtdiError("Foo")
        self.assertRaises(ftdi_chip.ReadError, self.device.read)
        mock_close.assert_called_once_with()

    def test_READ_SIZE_is_multiple_of_62(self):
        self.assertTrue(ftdi_chip.READ_SIZE % 62 == 0)

    @patch.object(ftdi_chip, 'READ_SIZE')
    def test_read_calls_device_read_with_correct_size(self, mock_size):
        self.device.read()
        self.mock_device.read.assert_called_once_with(mock_size)

        self.mock_device.reset_mock()
        self.device.read(sentinel.read_size)
        self.mock_device.read.assert_called_once_with(sentinel.read_size)

    def test_read_returns_device_read(self):
        data = self.device.read()
        self.assertIs(data, self.mock_device.read.return_value)

    def test_read_raises_ClosedDeviceError_if_closed(self):
        self.device.close()
        self.assertRaises(ftdi_chip.ClosedDeviceError, self.device.read)

    @patch('pysparc.ftdi_chip.time.sleep')
    def test_read_raises_ReadError_on_failed_read(self, mock_sleep):
        self.mock_device.read.side_effect = \
            ftdi_chip.pylibftdi.FtdiError("Foo")
        self.assertRaisesRegexp(ftdi_chip.ReadError, "Foo",
                                self.device.read)

    @patch('pysparc.ftdi_chip.time.sleep')
    def test_read_retries_read_on_exception_at_least_three_times(self,
            mock_sleep):
        self.mock_device.read.side_effect = [
            ftdi_chip.pylibftdi.FtdiError(),
            ftdi_chip.pylibftdi.FtdiError(), None]
        self.device.read()

    @patch('pysparc.ftdi_chip.time.sleep')
    def test_read_waits_before_retry(self, mock_sleep):
        self.device.read()
        self.assertFalse(mock_sleep.called)
        self.mock_device.read.side_effect = \
            [ftdi_chip.pylibftdi.FtdiError(), None]
        self.device.read()
        mock_sleep.assert_called_once_with(ftdi_chip.RW_ERROR_WAIT)

    @patch.object(ftdi_chip.FtdiChip, 'close')
    def test_write_closes_device_if_exception(self, mock_close):
        self.mock_device.write.side_effect = \
            ftdi_chip.pylibftdi.FtdiError("Foo")
        self.assertRaises(ftdi_chip.WriteError, self.device.write,
                          sentinel.data)
        mock_close.assert_called_once_with()

    def test_write_calls_device_write(self):
        self.device.write(sentinel.data)
        self.mock_device.write.assert_called_once_with(sentinel.data)

    def test_write_raises_ClosedDeviceError_if_closed(self):
        self.device.close()
        self.assertRaises(ftdi_chip.ClosedDeviceError, self.device.write,
                          sentinel.data)

    @patch('pysparc.ftdi_chip.time.sleep')
    def test_write_raises_WriteError_on_failed_write(self, mock_sleep):
        self.mock_device.write.side_effect = \
            ftdi_chip.pylibftdi.FtdiError("Foo")
        self.assertRaisesRegexp(ftdi_chip.WriteError, "Foo",
                                self.device.write, sentinel.data)

    @patch('pysparc.ftdi_chip.time.sleep')
    def test_write_retries_write_on_exception_three_times(self,
                                                          mock_sleep):
        self.mock_device.write.side_effect = [
            ftdi_chip.pylibftdi.FtdiError(),
            ftdi_chip.pylibftdi.FtdiError(), None]
        self.device.write(sentinel.data)

    @patch('pysparc.ftdi_chip.time.sleep')
    def test_write_waits_before_retry(self, mock_sleep):
        self.device.write('foo')
        self.assertFalse(mock_sleep.called)
        self.mock_device.write.side_effect = \
            [ftdi_chip.pylibftdi.FtdiError(), None]
        self.device.write('foo')
        mock_sleep.assert_called_once_with(ftdi_chip.RW_ERROR_WAIT)


class FtdiChipTestWithClosedDevice(unittest.TestCase):

    # Because we patch the 'open' method, the device is not opened in the
    # setUp call, and should still be closed
    @patch.object(ftdi_chip.FtdiChip, 'open')
    def setUp(self, mock_open):
        self.device = ftdi_chip.FtdiChip()

    def test_device_is_closed_if_not_opened(self):
        self.assertTrue(self.device.closed)

    @patch('pysparc.ftdi_chip.pylibftdi.Device')
    def test_open_opens_device_with_parameters(self, mock_Device):
        self.device._device_description = sentinel.description
        self.device._interface_select = sentinel.interface_select
        self.device.open()
        mock_Device.assert_called_once_with(sentinel.description,
            interface_select=sentinel.interface_select)

    @patch('pysparc.ftdi_chip.pylibftdi.Device')
    def test_open_stores_device(self, mock_Device):
        mock_device = Mock()
        mock_Device.return_value = mock_device
        self.device.open()
        self.assertIs(self.device._device, mock_device)

    @patch('pysparc.ftdi_chip.pylibftdi.Device')
    def test_open_raises_DeviceNotFoundError_if_not_present(self,
                                                            mock_Device):
        mock_Device.side_effect = ftdi_chip.pylibftdi.FtdiError(
            "FtdiError: device not found (-3)")
        self.assertRaises(ftdi_chip.DeviceNotFoundError,
                          self.device.open)

    @patch('pysparc.ftdi_chip.pylibftdi.Device')
    def test_open_raises_DeviceError_if_no_rights(self, mock_Device):
        # This occurs on OS X Mavericks.  You'll have to unload the driver
        # from OS X:
        # $ sudo kextunload -b com.apple.driver.AppleUSBFTDI
        mock_Device.side_effect = ftdi_chip.pylibftdi.FtdiError(
            "unable to claim usb device. Make sure the default FTDI driver is not in use (-5)")
        self.assertRaises(ftdi_chip.DeviceError,
                          self.device.open)

    @patch('pysparc.ftdi_chip.pylibftdi.Device')
    def test_open_raises_DeviceError_if_error_and_returns_ftdi_msg(self,
        mock_Device):

        msg = "Foobaz"
        mock_Device.side_effect = ftdi_chip.pylibftdi.FtdiError(msg)
        self.assertRaisesRegexp(ftdi_chip.DeviceError, msg,
                                self.device.open)

    @patch('pysparc.ftdi_chip.pylibftdi.Device')
    def test_open_sets_latency_timer(self, mock_Device):
        # explicitly set timer, required on some linux systems
        mock_device = mock_Device.return_value
        self.device.open()
        mock_device.ftdi_fn.ftdi_set_latency_timer.assert_called_once_with(16)

    @patch('pysparc.ftdi_chip.pylibftdi.Device')
    @patch.object(ftdi_chip.FtdiChip, 'flush')
    def test_open_calls_flush(self, mock_flush, mock_Device):
        self.device.open()
        mock_flush.assert_called_once_with()

    @patch('pysparc.ftdi_chip.pylibftdi.Device')
    def test_open_only_opens_once(self, mock_Device):
        self.device.open()
        mock_Device.reset_mock()
        self.device.open()
        self.assertFalse(mock_Device.called)

    @patch('pysparc.ftdi_chip.pylibftdi.Device')
    def test_open_sets_closed_to_false(self, mock_Device):
        self.device.closed = True
        self.device.open()
        self.assertFalse(self.device.closed)


if __name__ == '__main__':
    unittest.main()
