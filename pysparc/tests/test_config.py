import unittest
import weakref

from mock import patch, sentinel, Mock, MagicMock, call, ANY

import pysparc.config


class ConfigTest(unittest.TestCase):

    def setUp(self):
        self.mock_device = Mock()
        self.config = pysparc.config.Config(self.mock_device)

    def test_init_stores_weakref_to_device(self):
        # Keep a weak reference to the device, so the garbage collector
        # can clean up when a device class instance is deleted.
        self.assertEqual(self.config._device, weakref.ref(self.mock_device))

    @patch.object(pysparc.config.Config, 'get_member')
    def test_get_range_from_calls_get_member(self, mock_get_member):
        try:
            self.config._get_range_from(sentinel.name)
        except:
            pass
        mock_get_member.assert_called_once_with(sentinel.name)

    @patch.object(pysparc.config.Config, 'get_member')
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
                self.assertEqual(low, 0x000)
                self.assertEqual(high, 0xfff)
                self.assertEqual(value, (200 + 50) if level == 'low' else
                                 (200 + 120))

    def test_integration_times(self):
        for channel in [1, 2]:
            name = 'ch%d_integrator_time' % channel
            low, high = self.config._get_range_from(name)
            value = getattr(self.config, name)
            self.assertEqual(low, 0x00)
            self.assertEqual(high, 0xff)
            self.assertEqual(value, 0xff)

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

    @patch.object(pysparc.config.Config, '_observe_trigger_condition')
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


class ReadWriteConfigTest(unittest.TestCase):

    def setUp(self):
        self.mock_device = Mock()
        self.section = self.mock_device.description
        self.config = pysparc.config.Config(self.mock_device)

    def test_write_config_creates_section_with_description_if_not_exists(self):
        mock_configparser = Mock()

        # At first, the section does not exist, test that that is checked
        mock_configparser.has_section.return_value = False
        self.config.write_config(mock_configparser)
        mock_configparser.has_section.assert_called_once_with(self.section)

        # Now, the section already exists, test to make sure really only
        # created once
        mock_configparser.has_section.return_value = True
        self.config.write_config(mock_configparser)
        mock_configparser.add_section.assert_called_once_with(
            self.section)

    def test_write_config_sets_all_members_except_device(self):
        mock_configparser = Mock()
        self.config.write_config(mock_configparser)
        for member in self.config.members():
            if (member != '_device' and member not in
                self.config._private_settings):
                mock_configparser.set.assert_any_call(
                    self.section, member, getattr(self.config, member))
        device_call = call.set(self.section, '_device', ANY)
        assert device_call not in mock_configparser.mock_calls
        for private_setting in self.config._private_settings:
            device_call = call.set(self.section, private_setting, ANY)
            assert device_call not in mock_configparser.mock_calls

    @patch.object(pysparc.config.Config, '__setattr__')
    @patch.object(pysparc.config, 'literal_eval')
    def test_read_config_gets_all_members_except_device(self, mock_eval,
                                                        mock_setattr):
        eval_value = mock_eval.return_value

        mock_configparser = Mock()

        self.config.read_config(mock_configparser)
        for member in self.config.members():
            if member != '_device':
                mock_configparser.get.assert_any_call(
                    self.section, member)
                mock_setattr.assert_any_call(member, eval_value)
        device_call = call.get(self.section, '_device')
        assert device_call not in mock_configparser.mock_calls


class WriteSettingTest(unittest.TestCase):

    def setUp(self):
        self.patcher1 = patch.object(pysparc.config.Config, '_get_range_from')
        self.patcher2 = patch.object(pysparc.config, 'map_setting')
        self.patcher3 = patch('pysparc.config.SetControlParameter')
        self.mock_get_range_from = self.patcher1.start()
        self.mock_map_setting = self.patcher2.start()
        self.mock_map_setting.return_value = sentinel.setting_value
        self.mock_Message = self.patcher3.start()

        self.mock_device = Mock()
        self.config = pysparc.config.Config(self.mock_device)

        self.mock_get_range_from.return_value = sentinel.low, sentinel.high
        self.mock_setting = {'name': sentinel.name, 'value': sentinel.value}

    def tearDown(self):
        self.patcher1.stop()
        self.patcher2.stop()
        self.patcher3.stop()

    def test_write_byte_setting_to_device_calls_get_range_from(self):
        self.config._write_byte_setting_to_device(self.mock_setting)
        self.mock_get_range_from.assert_called_once_with(sentinel.name)

    def test_write_byte_setting_to_device_calls_map_setting(self):
        self.config._write_byte_setting_to_device(self.mock_setting)
        self.mock_map_setting.assert_called_once_with(
            sentinel.value, sentinel.low, sentinel.high, 0x00, 0xff)

    def test_write_byte_setting_to_device_creates_message(self):
        self.config._write_byte_setting_to_device(self.mock_setting)
        self.mock_Message.assert_called_once_with(sentinel.name,
                                                  sentinel.setting_value)

    def test_write_byte_setting_to_device_writes_to_device(self):
        self.config._write_byte_setting_to_device(self.mock_setting)
        msg = self.mock_Message.return_value
        self.mock_device.send_message.assert_called_once_with(msg)


class TriggerSettingsTest(unittest.TestCase):

    def test_build_trigger_condition(self):
        # shorthand notation
        trig = pysparc.config.Config.build_trigger_condition
        test = lambda x, y: self.assertEqual(trig(**x), y)
        self._assert_trigger_conditions(test)

    def test_unpack_trigger_condition(self):
        # shorthand notation
        trig = pysparc.config.Config.unpack_trigger_condition
        # set sensible defaults
        deflt = dict(num_low=0, num_high=0, or_not_and=False,
                     use_external=False, calibration_mode=False)
        # test function takes defaults and updates them with test values and
        # compares with the unpack_trigger_condition output
        test = lambda x, y: self.assertEqual(dict(deflt, **x),
                                             trig(y))
        self._assert_trigger_conditions(test)

    def _assert_trigger_conditions(self, test):
        test(dict(num_low=1, num_high=0, or_not_and=False), 0b00000001)
        test(dict(num_low=4, num_high=0, or_not_and=False), 0b00000100)

        test(dict(num_low=0, num_high=1, or_not_and=False), 0b00001000)
        test(dict(num_low=0, num_high=4, or_not_and=False), 0b00100000)
        test(dict(num_low=3, num_high=1, or_not_and=False), 0b00001011)

        test(dict(num_low=1, num_high=1, or_not_and=True), 0b00001100)
        test(dict(num_low=4, num_high=3, or_not_and=True), 0b00011111)
        test(dict(num_low=4, num_high=4, or_not_and=True), 0b00100111)

        test(dict(use_external=True), 0b01000000)
        test(dict(num_low=3, num_high=1, or_not_and=False, use_external=True),
             0b01001011)
        test(dict(num_low=4, num_high=3, or_not_and=True, use_external=True),
             0b01011111)

        test(dict(calibration_mode=True), 0b10000000)


if __name__ == '__main__':
    unittest.main()
