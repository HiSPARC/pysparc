import struct
import logging

from atom.api import Atom, observe, Range, Value

from pysparc.util import map_setting
from pysparc.messages import SetControlParameter


logger = logging.getLogger(__name__)


class NewConfig(Atom):

    ch1_voltage = Range(300, 1500, 300)
    ch2_voltage = Range(300, 1500, 300)
    ch1_threshold_low = Range(0, 2000, 30)
    ch2_threshold_low = Range(0, 2000, 30)
    ch1_threshold_high = Range(0, 2000, 70)
    ch2_threshold_high = Range(0, 2000, 70)

    ch1_offset_positive = Range(0x00, 0xff, 0x80)
    ch1_offset_negative = Range(0x00, 0xff, 0x80)
    ch2_offset_positive = Range(0x00, 0xff, 0x80)
    ch2_offset_negative = Range(0x00, 0xff, 0x80)
    ch1_gain_positive = Range(0x00, 0xff, 0x80)
    ch1_gain_negative = Range(0x00, 0xff, 0x80)
    ch2_gain_positive = Range(0x00, 0xff, 0x80)
    ch2_gain_negative = Range(0x00, 0xff, 0x80)
    common_offset = Range(0x00, 0xff, 0x00)
    full_scale = Range(0x00, 0xff, 0x00)

    trigger_condition = Range(0x01, 0xff, 0x08)

    _device = Value()

    def __init__(self, device):
        super(NewConfig, self).__init__()
        self._device = device

    @observe('ch1_offset_positive',
             'ch1_offset_negative',
             'ch2_offset_positive',
             'ch2_offset_negative',
             'ch1_gain_positive',
             'ch1_gain_negative',
             'ch2_gain_positive',
             'ch2_gain_negative',
             'common_offset',
             'full_scale')
    def _write_setting_to_device(self, setting):
        name, value = setting['name'], setting['value']
        low, high = self._get_range_from(name)
        setting_value = map_setting(value, low, high, 0x00, 0xff)
        msg = SetControlParameter(name, setting_value)
        self._device.send_message(msg)

    def _observe_trigger_condition(self, value):
        msg = SetControlParameter('trigger_condition', value['value'])
        self._device.send_message(msg)

    def _get_range_from(self, name):
        """Get the low, high range from an atom Range object.

        :param name: name of the range attribute
        :returns: (low, high) values of the range

        """
        atom = self.get_member(name)
        validator, (low, high) = atom.validate_mode
        return low, high


class Config(object):
    def __init__(self, device):
        self.__dict__['_device'] = {'id': 0, 'value': device, 'length': 0}

        self.__dict__['_channel1_offset_positive'] = {'id': 0x10, 'value': 0x80, 'length': 1}
        self.__dict__['_channel1_offset_negative'] = {'id': 0x11, 'value': 0x80, 'length': 1}
        self.__dict__['_channel1_gain_positive'] = {'id': 0x14, 'value': 0x80, 'length': 1}
        self.__dict__['_channel1_gain_negative'] = {'id': 0x15, 'value': 0x80, 'length': 1}
        self.__dict__['_channel1_integrator_time'] = {'id': 0x1a, 'value': 0xff, 'length': 1}
        self.__dict__['_channel1_pmt_high_voltage'] = {'id': 0x1e, 'value': 0x00, 'length': 1}
        self.__dict__['_channel1_threshold_low'] = {'id': 0x20, 'value': 0x0100, 'length': 2}
        self.__dict__['_channel1_threshold_high'] = {'id': 0x21, 'value': 0x0800, 'length': 2}

        self.__dict__['_channel2_offset_positive'] = {'id': 0x12, 'value': 0x80, 'length': 1}
        self.__dict__['_channel2_offset_negative'] = {'id': 0x13, 'value': 0x80, 'length': 1}
        self.__dict__['_channel2_gain_positive'] = {'id': 0x16, 'value': 0x80, 'length': 1}
        self.__dict__['_channel2_gain_negative'] = {'id': 0x17, 'value': 0x80, 'length': 1}
        self.__dict__['_channel2_integrator_time'] = {'id': 0x1b, 'value': 0xff, 'length': 1}
        self.__dict__['_channel2_pmt_high_voltage'] = {'id': 0x1f, 'value': 0x00, 'length': 1}
        self.__dict__['_channel2_threshold_low'] = {'id': 0x22, 'value': 0x0100, 'length': 2}
        self.__dict__['_channel2_threshold_high'] = {'id': 0x23, 'value': 0x0800, 'length': 2}

        self.__dict__['_common_offset'] = {'id': 0x18, 'value': 0x00, 'length': 1}
        self.__dict__['_full_scale'] = {'id': 0x19, 'value': 0x00, 'length': 1}
        self.__dict__['_comparator_threshold_low'] = {'id': 0x1c, 'value': 0x58, 'length': 1}
        self.__dict__['_comparator_threshold_high'] = {'id': 0x1d, 'value': 0xe6, 'length': 1}
        self.__dict__['_trigger_condition'] = {'id': 0x30, 'value': 0x08, 'length': 1}
        self.__dict__['_pre_coincidence_time'] = {'id': 0x31, 'value': 0x00c8, 'length': 2}
        self.__dict__['_coincidence_time'] = {'id': 0x32, 'value': 0x0190, 'length': 2}
        self.__dict__['_post_coincidence_time'] = {'id': 0x33, 'value': 0x0190, 'length': 2}

    def __setattr__(self, name, value):
        self.__dict__['_' + name]['value'] = value

        parameter = self.__dict__['_' + name]

        if parameter['length'] == 1:
            message = struct.pack('4B', 0x99, parameter['id'], value, 0x66)
        elif parameter['length'] == 2:
            message = struct.pack('5B', 0x99, parameter['id'], ((value >> 8) & 0xff), (value & 0xff), 0x66)
        else:
            message = None

        if self.device != None and message != None:
            self.device.master.write(message)

    def __getattr__(self, name):
        return self.__dict__['_' + name]['value']


if __name__ == '__main__':
    c = Config(None)

    c.common_offset = 0xff
