import unittest
import weakref

from mock import patch, Mock, MagicMock, sentinel, call

from pysparc import hardware, ftdi_chip, messages


class HiSPARCIIITest(unittest.TestCase):

    def test_description(self):
        self.assertEqual(hardware.HiSPARCIII.description,
                         "HiSPARC III Master")

    @patch.object(hardware.HiSPARCIII, '__init__')
    @patch.object(hardware.HiSPARCIII, '_burn_firmware')
    @patch('time.sleep')
    @patch('pysparc.hardware.FtdiChip')
    def test_open(self, mock_Device, mock_sleep, mock_burn, mock_init):
        # Using a manager with child mocks allows us to test for the order of
        # calls (see below). The manager itself is not used.
        manager = Mock()
        manager.attach_mock(mock_burn, 'burn')
        manager.attach_mock(mock_sleep, 'sleep')
        manager.attach_mock(mock_Device, 'Device')
        mock_init.return_value = None

        hisparc = hardware.HiSPARCIII()
        hisparc.open()

        expected = [call.burn(), call.sleep(.5),
                    call.Device(hardware.HiSPARCIII.description,
                                interface_select=2)]
        self.assertEqual(manager.mock_calls, expected)


class HiSPARCIITest(unittest.TestCase):

    @patch.object(hardware.BaseHardware, '__init__')
    @patch('pysparc.hardware.config.Config')
    @patch.object(hardware.HiSPARCII, 'reset_hardware')
    def setUp(self, mock_reset, mock_Config, mock_super):
        self.mock_super = mock_super
        self.mock_Config = mock_Config
        self.mock_config = mock_Config.return_value
        self.mock_reset = mock_reset
        self.mock_device = Mock()

        self.hisparc = hardware.HiSPARCII()
        self.hisparc._device = self.mock_device
        self.hisparc._buffer = MagicMock()

    def test_description(self):
        self.assertEqual(hardware.HiSPARCII.description,
                         "HiSPARC II Master")

    def test_init_calls_super(self):
        # test that super *was* called during setUp()
        self.mock_super.assert_called_once_with()

    def test_init_creates_device_configuration(self):
        self.mock_Config.assert_called_once_with(self.hisparc)
        self.assertIs(self.hisparc.config, self.mock_config)

    def test_init_calls_reset(self):
        self.mock_reset.assert_called_once_with()

    @patch.object(hardware.HiSPARCII, 'send_message')
    @patch('pysparc.hardware.ResetMessage')
    @patch('pysparc.hardware.InitializeMessage')
    def test_reset_hardware(self, mock_Init_msg, mock_Reset_msg,
                            mock_send):
        self.hisparc.config = Mock()
        self.hisparc.reset_hardware()
        msg1 = mock_Reset_msg.return_value
        msg2 = mock_Init_msg.return_value
        mock_send.assert_has_calls([call(msg1), call(msg2)])
        self.hisparc.config.reset_hardware.assert_called_once_with()

    @patch.object(hardware.HiSPARCII, 'read_into_buffer')
    @patch('pysparc.hardware.HisparcMessageFactory')
    def test_read_message(self, mock_factory, mock_read_into_buffer):
        self.hisparc.read_message()
        mock_read_into_buffer.assert_called_once_with()

    @patch('pysparc.hardware.HisparcMessageFactory')
    def test_read_message_calls_message_factory(self, mock_factory):
        self.hisparc.read_message()
        mock_factory.assert_called_once_with(self.hisparc._buffer)

    @patch('pysparc.hardware.HisparcMessageFactory')
    def test_read_message_sets_config_parameters(self, mock_factory):
        mock_config_message = Mock(spec=messages.ControlParameterList)
        mock_other_message = Mock()

        mock_factory.return_value = mock_other_message
        self.hisparc.read_message()
        self.assertFalse(self.mock_config.update_from_config_message.called)

        mock_factory.return_value = mock_config_message
        self.hisparc.read_message()
        self.mock_config.update_from_config_message.assert_called_once_with(
            mock_config_message)

    @patch('pysparc.hardware.HisparcMessageFactory')
    def test_read_message_returns_message(self, mock_factory):
        mock_factory.return_value = sentinel.msg
        actual = self.hisparc.read_message()
        self.assertIs(actual, sentinel.msg)

    @patch('pysparc.hardware.HisparcMessageFactory')
    def test_read_message_returns_config_message(self, mock_factory):
        mock_config_message = Mock(spec=messages.ControlParameterList)
        mock_factory.return_value = mock_config_message
        actual = self.hisparc.read_message()
        self.assertIs(actual, mock_config_message)

    @patch.object(hardware.HiSPARCII, 'flush_device')
    @patch.object(hardware.HiSPARCII, 'read_message')
    def test_flush_and_get_measured_data_message_calls_flush(self,
            mock_read, mock_flush):
        self.hisparc.flush_and_get_measured_data_message(timeout=.01)
        mock_flush.assert_called_once_with()

    @patch.object(hardware.HiSPARCII, 'read_message')
    def test_flush_and_get_measured_data_message_calls_read_message(self,
            mock_read):
        self.hisparc.flush_and_get_measured_data_message(timeout=.01)
        self.assertTrue(mock_read.called)

    @patch.object(hardware.HiSPARCII, 'read_message')
    def test_flush_and_get_measured_data_message_returns_correct_type(
            self, mock_read):
        mock_msg = Mock(spec=messages.MeasuredDataMessage)
        mock_read.side_effect = [Mock(), Mock(), mock_msg, Mock()]
        msg = self.hisparc.flush_and_get_measured_data_message(
            timeout=.01)
        self.assertIs(msg, mock_msg)


class BaseHardwareTest(unittest.TestCase):

    @patch.object(hardware.BaseHardware, 'open')
    def setUp(self, mock_open):
        self.mock_open = mock_open
        self.mock_device = Mock()
        self.hisparc = hardware.BaseHardware()
        self.hisparc._device = self.mock_device
        self.mock_device.closed = False

    def test_description(self):
        self.assertEqual(hardware.BaseHardware.description,
                         "BaseHardware")

    def test_device_is_none_before_instantiation(self):
        self.assertIs(hardware.BaseHardware._device, None)

    def test_init_calls_open(self):
        self.mock_open.assert_called_once_with()

    @patch('pysparc.hardware.FtdiChip')
    def test_open_opens_and_saves_device(self, mock_Device):
        mock_device = Mock()
        mock_Device.return_value = mock_device

        self.hisparc.open()

        mock_Device.assert_called_once_with(self.hisparc.description)
        self.assertIs(self.hisparc._device, mock_device)

    @patch.object(hardware.BaseHardware, 'close')
    def test_destructor_calls_close(self, mock_close):
        del self.hisparc
        mock_close.assert_called_once_with()

    def test_close_closes_device(self):
        self.hisparc.close()
        self.mock_device.close.assert_called_once_with()

    def test_close_does_nothing_if_device_is_closed(self):
        self.mock_device.closed = True
        self.hisparc.close()
        self.assertFalse(self.mock_device.close.called)

    def test_close_does_nothing_if_device_is_none(self):
        self.hisparc._device = None
        self.hisparc.close()
        self.assertFalse(self.mock_device.close.called)

    def test_buffer_is_none_before_instantiation(self):
        self.assertIs(hardware.BaseHardware._buffer, None)

    def test_buffer_attribute_is_bytearray(self):
        self.assertIs(type(self.hisparc._buffer), bytearray)

    def test_flush_device_flushes_device(self):
        self.hisparc._buffer = MagicMock()
        self.hisparc.flush_device()
        self.mock_device.flush.assert_called_once_with()

    def test_flush_device_clears_buffer(self):
        self.hisparc._buffer = bytearray([0x1, 0x2, 0x3])
        self.hisparc.flush_device()
        self.assertEqual(len(self.hisparc._buffer), 0)

    def test_send_message_calls_msg_encode(self):
        msg = Mock()
        self.hisparc.send_message(msg)
        msg.encode.assert_called_once_with()

    def test_send_message_writes_to_device(self):
        msg = Mock()
        msg.encode.return_value = sentinel.encoded_msg
        self.hisparc.send_message(msg)
        self.mock_device.write.assert_called_once_with(
            sentinel.encoded_msg)

    def test_read_into_buffer_reads_from_device(self):
        self.hisparc._buffer = MagicMock()
        self.mock_device.read.return_value = MagicMock()
        self.hisparc.read_into_buffer()
        self.mock_device.read.assert_called_once_with(hardware.READ_SIZE)

    def test_read_into_buffer_reads_into_buffer(self):
        mock_buffer = Mock()
        self.hisparc._buffer = mock_buffer
        read_data = self.mock_device.read.return_value
        self.hisparc.read_into_buffer()
        mock_buffer.extend.assert_called_once_with(read_data)

    @patch.object(hardware.BaseHardware, 'read_into_buffer')
    def test_read_message(self, mock_read_into_buffer):
        self.assertRaises(NotImplementedError, self.hisparc.read_message)
        mock_read_into_buffer.assert_called_once_with()


class TrimbleGPSTest(unittest.TestCase):

    # mock __init__ of the parent class, so we do not depend on that
    # implementation
    @patch.object(hardware.TrimbleGPS, '__init__')
    def setUp(self, mock_init):
        mock_init.return_value = None

        self.gps = hardware.TrimbleGPS()
        self.gps._buffer = sentinel.buffer
        self.mock_device = Mock()
        self.gps._device = self.mock_device

        patcher1 = patch.object(hardware.TrimbleGPS, 'read_into_buffer')
        patcher2 = patch('pysparc.hardware.GPSMessageFactory')
        self.mock_read_into_buffer = patcher1.start()
        self.mock_factory = patcher2.start()

        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)

    def test_type_is_basehardware(self):
        self.assertIsInstance(self.gps, hardware.BaseHardware)

    @patch.object(hardware.BaseHardware, 'open')
    def test_open_calls_super(self, mock_super):
        self.gps.open()
        mock_super.assert_called_once_with()

    @patch.object(hardware.BaseHardware, 'open')
    def test_open_sets_line_settings(self, mock_super):
        self.gps.open()
        self.gps._device.set_line_settings.assert_called_once_with(
            ftdi_chip.BITS_8, ftdi_chip.PARITY_ODD, ftdi_chip.STOP_BIT_1)

    def test_description(self):
        self.assertEqual(hardware.TrimbleGPS.description,
                         "FT232R USB UART")

    def test_read_message(self):
        self.gps.read_message()
        self.mock_read_into_buffer.assert_called_once_with()

    def test_read_message_calls_message_factory(self):
        self.gps.read_message()
        self.mock_factory.assert_called_once_with(sentinel.buffer)

    def test_read_message_returns_message(self):
        self.mock_factory.return_value = sentinel.msg
        actual = self.gps.read_message()
        self.assertIs(actual, sentinel.msg)


if __name__ == '__main__':
    unittest.main()
