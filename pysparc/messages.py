"""Process HiSPARC hardware messages

Parse and operate on messages from and to the HiSPARC II / III hardware.

:class:`HisparcMessage`: factory class for HiSPARC messages

"""
import struct
from struct import Struct
import datetime
import numpy as np


codons = {'start': 0x99, 'stop': 0x66}
msg_ids = {'measured_data': 0xa0,
           'comparator_data': 0xa2,
           'one_second': 0xa4,
           'all_controls': 0x55,
           'communication_error': 0x88,
          }
error_ids = {'header_not_detected': 0x99,
             'identifier_unknown': 0x89,
             'stop_codon_not_detected': 0x66,
            }
command_ids = {'soft_reset': 0xff,
               'set_all_controls': 0x50,
               'get_all_controls': 0x55,
              }


class MessageError(Exception):
    pass


class HisparcMessage(object):

    """HiSPARC Message base/factory class

    Base and factory class for HiSPARC hardware messages.

    """
    identifier = None

    def __init__(self):
        self.info = []
        self.data = []

    @classmethod
    def is_message_for(cls, buff):
        cls.validate_message_start(buff)
        if buff[1] == cls.identifier:
            return True
        else:
            return False

    @classmethod
    def validate_message_start(cls, buff):
        if type(buff) != bytearray:
            raise MessageError("Buffer must be of type bytearray")
        if buff[0] != codons['start']:
            raise MessageError("First byte of buffer is not start codon")

    def validate_codons_and_id(self, header, identifier, end):
        if (header != codons['start'] or end != codons['stop'] or
            identifier != self.identifier):
            raise MessageError("Corrupt message detected: %x %x %x" %
                (header, identifier, end))

    def encode(self):
        if None is self.identifier:
            return ''

        format = ('2B%(info)ds%(data)dsB' %
                  {'info': len(str(bytearray(self.info))),
                   'data': len(str(bytearray(self.data)))})
        packer = Struct(format)

        return packer.pack(0x99, self.identifier, str(bytearray(self.info)),
                           str(bytearray(self.data)), 0x66)


class OneSecondMessage(HisparcMessage):
    identifier = msg_ids['one_second']
    msg_format = '>2B2BH3B2I4H61s1B'

    def __init__(self, buff):
        self.parse_message(buff)

    def parse_message(self, buff):
        msg_length = struct.calcsize(self.msg_format)
        str_buff = str(buff[:msg_length])

        (header, identifier, self.gps_day, self.gps_month, self.gps_year,
         self.gps_hours, self.gps_minutes, self.gps_seconds,
         self.count_ticks_PPS, self.quantization_error,
         self.count_ch2_high, self.count_ch2_low, self.count_ch1_high,
         self.count_ch1_low, self.satellite_info, end) = \
            struct.unpack_from(self.msg_format, str_buff)

        self.validate_codons_and_id(header, identifier, end)
        del buff[:msg_length]

        self.timestamp = datetime.datetime(self.gps_year, self.gps_month,
                                           self.gps_day, self.gps_hours,
                                           self.gps_minutes,
                                           self.gps_seconds)

    def __str__(self):
        return 'One second message: %s' % self.timestamp


class MeasuredDataMessage(HisparcMessage):
    identifier = msg_ids['measured_data']
    msg_format = '>2BB4H2BH3BI'
    msg_tail_format = '>%dsB'

    def __init__(self, buff):
        self.parse_message(buff)

    def parse_message(self, buff):
        msg_length = struct.calcsize(self.msg_format)
        str_buff = str(buff[:msg_length])

        (header, identifier, self.trigger_condition, self.trigger_pattern,
         self.pre_coincidence_time, self.coincidence_time,
         self.post_coincidence_time, self.gps_day, self.gps_month,
         self.gps_year, self.gps_hours, self.gps_minutes,
         self.gps_seconds, self.count_ticks_PPS) = \
            struct.unpack_from(self.msg_format, str_buff)

        event_length = self.pre_coincidence_time + self.coincidence_time + \
                       self.post_coincidence_time
        # 12 bits * 2 adcs / (8 bits / byte)
        trace_length = 3 * event_length
        # message contains data from two channels
        msg_tail_format = self.msg_tail_format % (2 * trace_length)
        msg_tail_length = struct.calcsize(msg_tail_format)
        total_length = msg_length + msg_tail_length
        str_buff = str(buff[msg_length:total_length])

        self.raw_traces, end = struct.unpack_from(msg_tail_format,
                                                  str_buff)

        self.validate_codons_and_id(header, identifier, end)
        del buff[:total_length]

        self.trace_length = trace_length
        self.timestamp = datetime.datetime(self.gps_year, self.gps_month,
                                           self.gps_day, self.gps_hours,
                                           self.gps_minutes,
                                           self.gps_seconds)

    def __str__(self):
        return 'Event message: %s' % self.timestamp

    def __getattr__(self, name):
        """Create missing attributes on demand"""

        if name == 'trace_ch1':
            self.trace_ch1 = self._get_trace(ch=1)
            return self.trace_ch1
        elif name == 'trace_ch2':
            self.trace_ch2 = self._get_trace(ch=2)
            return self.trace_ch2
        elif name == 'adc_ch1_pos':
            return self.trace_ch1[::2]
        elif name == 'adc_ch1_neg':
            return self.trace_ch1[1::2]
        elif name == 'adc_ch2_pos':
            return self.trace_ch2[::2]
        elif name == 'adc_ch2_neg':
            return self.trace_ch2[1::2]
        else:
            raise AttributeError(
                "MeasuredDataMessage instance has no attribute '%s'" % name)

    def _get_trace(self, ch):
        """Get a trace for a given channel"""

        if ch not in [1, 2]:
            raise ValueError("Undefined signal channel: %d" % ch)
        else:
            idx_start = (ch - 1) * self.trace_length
            idx_stop = idx_start + self.trace_length
            raw_trace = self.raw_traces[idx_start:idx_stop]
            return self._unpack_raw_trace(raw_trace)

    def _unpack_raw_trace(self, raw_trace):
        """Unpack a raw trace from 2x12-bit sequences"""

        trace = []
        for samples in self._split_raw_trace(raw_trace):
            first = struct.unpack('>H', samples[:2])[0] >> 4
            second = struct.unpack('>H', samples[1:])[0] & 0xfff
            trace.extend([first, second])
        return np.array(trace)

    def _split_raw_trace(self, raw_trace):
        """Split a raw trace in groups of two 12-bit samples"""

        for i in xrange(0, len(raw_trace), 3):
            yield raw_trace[i:i + 3]


class ChannelOffsetAdjustMessage(HisparcMessage):
    def __init__(self, channel, positive = True, offset = 0x80):
        super(ChannelOffsetAdjustMessage, self).__init__()

        if 1 is channel:
            self.identifier = 0x10 if positive else 0x11
        if 2 is channel:
            self.identifier = 0x12 if positive else 0x13

        self.data = [offset]


class ChannelGainAdjustMessage(HisparcMessage):
    def __init__(self, channel, positive = True, gain = 0x80):
        super(ChannelGainAdjustMessage, self).__init__()

        if 1 is channel:
            self.identifier = 0x14 if positive else 0x15
        if 2 is channel:
            self.identifier = 0x16 if positive else 0x17

        self.data = [gain]


class CommonOffsetAdjustMessage(HisparcMessage):
    def __init__(self, offset = 0x00):
        super(CommonOffsetAdjustMessage, self).__init__()

        self.identifier = 0x18
        self.data = [offset]


class FullScaleAdjustHisparcMessage(HisparcMessage):
    def __init__(self, scale = 0x00):
        HisparcMessage.__init__(self)

        self.identifier = 0x19
        self.data = [scale]


class IntergratorTimeAdjustMessage(HisparcMessage):
    def __init__(self, channel, time = 0xff):
        super(IntergratorTimeAdjustMessage, self).__init__()

        if channel is 1 or channel is 2:
            self.identifier = 0x1a + (channel - 1)

        self.data = [time]


class ComperatorThresholdLowMessage(HisparcMessage):
    def __init__(self, low = True, threshold = None):
        super(ComperatorThresholdLowMessage, self).__init__()

        if None is threshold:
            threshold = 0x58 if low else 0xe6

        self.identifier = 0x1c if low else 0x1d
        self.data = [threshold]


class PMTHighVoltageAdjustMessage(HisparcMessage):
    def __init__(self, channel, voltage = 0x00):
        super(PMTHighVoltageAdjustMessage, self).__init__()

        if channel is 1 or channel is 2:
            self.identifier = 0x1e + (channel - 1)

        self.data = [voltage]


class ThresholdAdjustMessage(HisparcMessage):
    def __init__(self, channel, low = True, threshold = None):
        super(ThresholdAdjustMessage, self).__init__()

        if threshold is None:
            threshold = 0x0100 if low else 0x0800

        if channel is 1:
            self.identifier = 0x20 if low else 0x21
        if channel is 2:
            self.identifier = 0x22 if low else 0x23

        self.data = [((threshold >> 8) & 0xff), (threshold & 0xff)]


class TriggerConditionMessage(HisparcMessage):
    def __init__(self, condition = 0x08):
        super(TriggerConditionMessage, self).__init__()

        self.identifier = 0x30
        self.data = [condition]


class PreCoincidenceTimeMessage(HisparcMessage):
    def __init__(self, time = 0x00c8):
        super(PreCoincidenceTimeMessage, self).__init__()

        self.identifier = 0x31
        self.data = [((time >> 8) & 0xff), (time & 0xff)]


class CoincidenceTimeMessage(HisparcMessage):
    def __init__(self, time = 0x0190):
        super(CoincidenceTimeMessage, self).__init__()

        self.identifier = 0x32
        self.data = [((time >> 8) & 0xff), (time & 0xff)]


class PostCoincidenceTime(HisparcMessage):
    def __init__(self, time = 0x0190):
        super(PostCoincidenceTime, self).__init__()

        self.identifier = 0x33
        self.data = [((time >> 8) & 0xff), (time & 0xff)]


class InitializeMessage(HisparcMessage):
    def __init__(self, one_second_enabled = True):
        super(InitializeMessage, self).__init__()

        self.identifier = 0x35
        self.data = [0x00, 0x00, 0x00, 0x03 if one_second_enabled else 0x01]


class ResetMessage(HisparcMessage):
    def __init__(self, confirm = False):
        super(ResetMessage, self).__init__()

        self.identifier = 0xff


def HisparcMessageFactory(buff):
    """Return a message, extracted from the buffer

    Inspect the buffer and extract the first full message. A
    HisparcMessage subclass instance will be returned, according to
    the type of the message.

    :param buff: the contents of the usb buffer
    :return: instance of a HisparcMessage subclass

    """
    if len(buff) == 0:
        return None

    for cls in HisparcMessage.__subclasses__():
        if cls.is_message_for(buff):
            return cls(buff)
    raise NotImplementedError("Message type not implemented")
