import struct
import logging


logger = logging.getLogger(__name__)


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
