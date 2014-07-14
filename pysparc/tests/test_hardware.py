import unittest

from mock import patch, Mock, sentinel

from pysparc import hardware, ftdi_chip


class HiSPARCIIITest(unittest.TestCase):

    @patch('pysparc.hardware.FtdiChip')
    @patch('pysparc.hardware.config.Config')
    def setUp(self, mock_Config, mock_Device):
        self.mock_Config = mock_Config
        self.mock_config = mock_Config.return_value
        self.mock_Device = mock_Device
        self.mock_device = mock_Device.return_value
        self.mock_device.closed = False
        self.hisparc = hardware.HiSPARCIII()

    def test_description(self):
        self.assertEqual(hardware.HiSPARCIII._description, "HiSPARC III Master")

    def test_device_is_none_before_instantiation(self):
        self.assertIs(hardware.HiSPARCIII._device, None)

    def test_init_opens_device_with_description(self):
        self.mock_Device.assert_called_once_with(self.hisparc._description)

    def test_init_saves_device_as_attribute(self):
        self.assertIs(self.hisparc._device, self.mock_device)

    def test_init_creates_device_configuration(self):
        self.mock_Config.assert_called_once_with(self.hisparc)
        self.assertIs(self.hisparc.config, self.mock_config)

    def test_destructor_closes_device(self):
        self.hisparc.__del__()
        self.mock_device.close.assert_called_once_with()

    def test_destructor_does_nothing_if_device_is_closed(self):
        self.mock_device.closed = True
        self.hisparc.__del__()
        self.assertFalse(self.mock_device.close.called)

    def test_destructor_does_nothing_if_device_is_none(self):
        self.hisparc._device = None
        self.hisparc.__del__()
        self.assertFalse(self.mock_device.close.called)

    def test_buffer_is_none_before_instantiation(self):
        self.assertIs(hardware.HiSPARCIII._buffer, None)

    def test_buffer_attribute_is_bytearray(self):
        self.assertIs(type(self.hisparc._buffer), bytearray)

    def test_flush_device_flushes_device(self):
        self.hisparc.flush_device()
        self.mock_device.flush.assert_called_once_with()

    def test_flush_device_clears_buffer(self):
        self.hisparc._buffer.extend([0x1, 0x2, 0x3])
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
        self.mock_device.write.assert_called_once_with(sentinel.encoded_msg)

    @patch.object(hardware.HiSPARCIII, 'send_message')
    @patch('pysparc.hardware.ResetMessage')
    def test_reset_hardware_sends_reset_message(self, mock_Reset_msg, mock_send):
        self.hisparc.reset_hardware()
        msg = mock_Reset_msg.return_value
        mock_send.assert_called_once_with(msg)

    def test_read_into_buffer_reads_from_device(self):
        self.hisparc.read_into_buffer()
        self.mock_device.read.assert_called_once_with(ftdi_chip.BUFFER_SIZE)

    def test_read_into_buffer_reads_into_buffer(self):
        mock_buffer = Mock()
        self.hisparc._buffer = mock_buffer
        read_data = self.mock_device.read.return_value
        self.hisparc.read_into_buffer()
        mock_buffer.extend.assert_called_once_with(read_data)


if __name__ == '__main__':
    unittest.main()
