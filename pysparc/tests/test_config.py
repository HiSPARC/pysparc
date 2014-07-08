import unittest

from mock import patch, sentinel, Mock, MagicMock

import pysparc.config


class ConfigTest(unittest.TestCase):

    def setUp(self):
        self.mock_device = Mock()
        self.config = pysparc.config.NewConfig(self.mock_device)

    def test_init_stores_device(self):
        self.assertEqual(self.config._device, self.mock_device)

    @patch.object(pysparc.config.NewConfig, 'get_member')
    def test_get_range_from_calls_get_member(self, mock_get_member):
        try:
            self.config._get_range_from(sentinel.name)
        except:
            pass
        mock_get_member.assert_called_once_with(sentinel.name)

    @patch.object(pysparc.config.NewConfig, 'get_member')
    def test_get_range_from_returns_range(self, mock_get_member):
        mock_get_member.return_value.validate_mode = [
            sentinel.validator, (sentinel.low, sentinel.high)]
        low, high = self.config._get_range_from(sentinel.name)
        self.assertEqual(low, sentinel.low)
        self.assertEqual(high, sentinel.high)

    def test_voltage_settings(self):
        for channel in [1, 2]:
            name = 'ch%d_voltage' % channel
            low, high = self.config._get_range_from(name)
            value = getattr(self.config, name)
            self.assertEqual(low, 300)
            self.assertEqual(high, 1500)
            self.assertEqual(value, low)

    def test_threshold_settings(self):
        for channel in [1, 2]:
            for level in ['low', 'high']:
                name = 'ch%d_threshold_%s' % (channel, level)
                low, high = self.config._get_range_from(name)
                value = getattr(self.config, name)
                self.assertEqual(low, 0)
                self.assertEqual(high, 2000)
                self.assertEqual(value, 30 if level == 'low' else 70)

    def test_individual_gains_and_offsets(self):
        for channel in [1, 2]:
            for type in ['gain', 'offset']:
                for edge in ['positive', 'negative']:
                    name = 'ch%d_%s_%s' % (channel, type, edge)
                    low, high = self.config._get_range_from(name)
                    value = getattr(self.config, name)
                    self.assertEqual(low, 0x00)
                    self.assertEqual(high, 0xff)
                    self.assertEqual(value, 0x80)

    def test_common_gain_and_offset(self):
        # Unfortunately, the common gain is called 'full scale'
        for name in ['common_offset', 'full_scale']:
            low, high = self.config._get_range_from(name)
            value = getattr(self.config, name)
            self.assertEqual(low, 0x00)
            self.assertEqual(high, 0xff)
            self.assertEqual(value, 0x00)

    @patch.object(pysparc.config.NewConfig, '_observe_trigger_condition')
    def test_trigger_condition(self, mock_observer):
        low, high = self.config._get_range_from('trigger_condition')
        value = self.config.trigger_condition
        self.assertEqual(low, 0x01)
        self.assertEqual(high, 0xff)
        self.assertEqual(value, 0x08)

    @patch('pysparc.config.SetControlParameter')
    def test_observe_trigger_condition(self, mock_Message):
        mock_value = MagicMock()
        mock_value.__getitem__.return_value = sentinel.value
        self.config._observe_trigger_condition(mock_value)

        mock_value.__getitem__.assert_called_once_with('value')
        mock_Message.assert_called_once_with('trigger_condition',
                                             sentinel.value)
        msg = mock_Message.return_value
        self.mock_device.send_message.assert_called_once_with(msg)


class WriteSettingTest(unittest.TestCase):

    def setUp(self):
        self.patcher1 = patch.object(pysparc.config.NewConfig, '_get_range_from')
        self.patcher2 = patch.object(pysparc.config, 'map_setting')
        self.patcher3 = patch('pysparc.config.SetControlParameter')
        self.mock_get_range_from = self.patcher1.start()
        self.mock_map_setting = self.patcher2.start()
        self.mock_map_setting.return_value = sentinel.setting_value
        self.mock_Message = self.patcher3.start()

        self.mock_device = Mock()
        self.config = pysparc.config.NewConfig(self.mock_device)

        self.mock_get_range_from.return_value = sentinel.low, sentinel.high
        self.mock_setting = {'name': sentinel.name, 'value': sentinel.value}

    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        self.patcher3.stop()

    def test_write_setting_to_device_calls_get_range_from(self):
        self.config._write_setting_to_device(self.mock_setting)
        self.mock_get_range_from.assert_called_once_with(sentinel.name)

    def test_write_setting_to_device_calls_map_setting(self):
        self.config._write_setting_to_device(self.mock_setting)
        self.mock_map_setting.assert_called_once_with(sentinel.value,
            sentinel.low, sentinel.high, 0x00, 0xff)

    def test_write_setting_to_device_creates_message(self):
        self.config._write_setting_to_device(self.mock_setting)
        self.mock_Message.assert_called_once_with(sentinel.name,
                                                  sentinel.setting_value)

    def test_write_setting_to_device_writes_to_device(self):
        self.config._write_setting_to_device(self.mock_setting)
        msg = self.mock_Message.return_value
        self.mock_device.send_message.assert_called_once_with(msg)


if __name__ == '__main__':
    unittest.main()
