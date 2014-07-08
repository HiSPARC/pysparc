import struct
import logging

from atom.api import Atom, observe, Range, Value

from pysparc.util import map_setting
from pysparc.messages import SetControlParameter


logger = logging.getLogger(__name__)


class Config(Atom):

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
        super(Config, self).__init__()
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
