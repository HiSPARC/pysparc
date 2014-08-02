"""Process HiSPARC hardware messages

Parse and operate on messages from and to the HiSPARC II / III hardware.

:class:`HisparcMessage`: factory class for HiSPARC messages

"""

import struct
import datetime
import calendar

import numpy as np


codons = {'start': 0x99, 'stop': 0x66}

msg_ids = {'measured_data': 0xa0,
           'comparator_data': 0xa2,
           'one_second': 0xa4,
           'all_controls': 0x55,
           'communication_error': 0x88,
           'reset': 0xff,

           # config settings (INCOMPLETE)
           'ch1_offset_positive': 0x10,
           'ch1_offset_negative': 0x11,
           'ch2_offset_positive': 0x12,
           'ch2_offset_negative': 0x13,
           'ch1_gain_positive': 0x14,
           'ch1_gain_negative': 0x15,
           'ch2_gain_positive': 0x16,
           'ch2_gain_negative': 0x17,
           'common_offset': 0x18,
           'full_scale': 0x19,
           'ch1_voltage': 0x1e,
           'ch2_voltage': 0x1f,
           'ch1_threshold_low': 0x20,
           'ch1_threshold_high': 0x21,
           'ch2_threshold_low': 0x22,
           'ch2_threshold_high': 0x23,
           'trigger_condition': 0x30,
           'spare_bytes': 0x35,
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
    msg_format = ''

    def __init__(self):
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
        if buff[0] != codons['start']:
            raise MessageError("First byte of buffer is not start codon")

    def validate_codons_and_id(self, header, identifier, end):
        if (header != codons['start'] or end != codons['stop'] or
                identifier != self.identifier):
            raise MessageError("Corrupt message detected: %x %x %x" %
                               (header, identifier, end))

    def encode(self):
        if self.identifier is None:
            return None

        format = '>BB' + self.msg_format + 'B'
        packer = struct.Struct(format)
        data = [codons['start'], self.identifier]
        if self.data:
            data += self.data
        data.append(codons['stop'])
        msg = packer.pack(*data)
        return msg


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

        self.datetime = datetime.datetime(self.gps_year, self.gps_month,
                                          self.gps_day, self.gps_hours,
                                          self.gps_minutes,
                                          self.gps_seconds)
        self.timestamp = calendar.timegm(self.datetime.utctimetuple())

    def __str__(self):
        return 'One second message: %s %d %d %d %d' % (self.datetime,
                                                       self.count_ch1_low,
                                                       self.count_ch1_high,
                                                       self.count_ch2_low,
                                                       self.count_ch2_high)


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
         self.gps_seconds, self.nanoseconds) = \
            struct.unpack_from(self.msg_format, str_buff)

        event_length = (self.pre_coincidence_time + self.coincidence_time +
                        self.post_coincidence_time)
        # 12 bits * 2 adcs / (8 bits / byte)
        trace_length = 3 * event_length
        # message contains data from two channels
        msg_tail_format = self.msg_tail_format % (2 * trace_length)
        msg_tail_length = struct.calcsize(msg_tail_format)
        total_length = msg_length + msg_tail_length
        str_buff = str(buff[msg_length:total_length])

        self.raw_traces, end = struct.unpack_from(msg_tail_format, str_buff)

        self.validate_codons_and_id(header, identifier, end)
        del buff[:total_length]

        self.trace_length = trace_length
        self.datetime = datetime.datetime(self.gps_year, self.gps_month,
                                          self.gps_day, self.gps_hours,
                                          self.gps_minutes,
                                          self.gps_seconds)
        self.timestamp = calendar.timegm(self.datetime.utctimetuple())

    def __str__(self):
        bl1 = self.trace_ch1[:100].mean()
        ph1 = self.trace_ch1.max() - bl1

        bl2 = self.trace_ch2[:100].mean()
        ph2 = self.trace_ch2.max() - bl2

        return 'Event message: %s %d %d' % (self.datetime, ph1, ph2)


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
        """Unpack a raw trace from 12-bit sequences.

        This has to be very fast, since this must run on a Raspberry Pi
        and still be able to handle lots of events.  It uses some NumPy
        magic to accomplish this.  Rule #1: DO NOT LOOP.  Really, looping
        over thousands of samples and calling some function
        (struct.unpack, for example) is unbearably slow, even without
        doing anything.  Rule #2: do not create an array from thousands of
        values (e.g. np.array(result_from_struct_unpack)).  This is very
        slow. Rule #3: if you really must loop, DO NOT LOOP.  So, this
        code does not loop, and uses NumPy functions to create an array
        directly from binary data.  Bit manipulations are done on the
        entire array.
        """
        # convert every byte to a numerical value
        byte_values = np.fromstring(raw_trace, dtype=np.uint8)
        # cast to unsigned 16-bit, so there's room for 12-bit values
        values = byte_values.astype(np.uint16)

        # for every 3 bytes:
        # create array of first 12 bits
        a1 = (values[::3] << 4) + (values[1::3] >> 4)
        # create array of last 12 bits
        a2 = ((values[1::3] & 0x0f) << 8) + values[2::3]
        # stack them together and flatten to 1D-array
        return np.dstack((a1, a2)).ravel()


class SetControlParameter(HisparcMessage):

    def __init__(self, parameter, value, nbytes=1):
        super(SetControlParameter, self).__init__()
        self.identifier = msg_ids[parameter]
        self.data = [value]
        if nbytes == 1:
            self.msg_format = 'B'
        elif nbytes == 2:
            self.msg_format = 'H'
        else:
            raise NotImplementedError("nbytes out of range")


class InitializeMessage(HisparcMessage):

    identifier = msg_ids['spare_bytes']
    msg_format = 'I'

    def __init__(self, one_second_enabled=False):
        super(InitializeMessage, self).__init__()

        # bit 0 enables two-way communication
        data = 1
        if one_second_enabled:
            # bit 1 enables one-second messages from electronics
            data |= 0b10
        self.data = [data]


class ResetMessage(HisparcMessage):

    identifier = msg_ids['reset']


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
            try:
                return cls(buff)
            except:
                return None
    raise NotImplementedError("Message type not implemented")
