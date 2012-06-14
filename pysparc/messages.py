"""Process HiSPARC hardware messages

Parse and operate on messages from and to the HiSPARC II / III hardware.

:class:`HisparcMessage`: factory class for HiSPARC messages

"""
from struct import Struct


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
        cls.validate_message(buff)
        return False

    @classmethod
    def validate_message(cls, buff):
        if type(buff) != bytearray:
            raise MessageError("Buffer must be of type bytearray")
        if buff[0] != codons['start']:
            raise MessageError("First byte of buffer is not start codon")

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
    def __init__(self, buff):
        pass

    @classmethod
    def is_message_for(cls, buff):
        super(OneSecondMessage, cls).is_message_for(buff)
        if buff[1] == msg_ids['one_second']:
            return True
        else:
            return False


class ChannelOffsetAdjustMessage(HisparcMessage):
    def __init__(self, channel, positive = True, offset = 0x80):
        HisparcMessage.__init__(self)

        if 1 is channel:
            self.identifier = 0x10 if positive else 0x11
        if 2 is channel:
            self.identifier = 0x12 if positive else 0x13

        self.data = [offset]


class ChannelGainAdjustMessage(HisparcMessage):
    def __init__(self, channel, positive = True, gain = 0x80):
        HisparcMessage.__init__(self)

        if 1 is channel:
            self.identifier = 0x14 if positive else 0x15
        if 2 is channel:
            self.identifier = 0x16 if positive else 0x17

        self.data = [gain]


class CommonOffsetAdjustMessage(HisparcMessage):
    def __init__(self, offset = 0x00):
        HisparcMessage.__init__(self)

        self.identifier = 0x18
        self.data = [offset]


class FullScaleAdjustHisparcMessage(HisparcMessage):
    def __init__(self, scale = 0x00):
        HisparcMessage.__init__(self)

        self.identifier = 0x19
        self.data = [scale]


class IntergratorTimeAdjustMessage(HisparcMessage):
    def __init__(self, channel, time = 0xff):
        HisparcMessage.__init__(self)

        if channel is 1 or channel is 2:
            self.identifier = 0x1a + (channel - 1)

        self.data = [time]


class ComperatorThresholdLowMessage(HisparcMessage):
    def __init__(self, low = True, threshold = None):
        HisparcMessage.__init__(self)

        if None is threshold:
            threshold = 0x58 if low else 0xe6

        self.identifier = 0x1c if low else 0x1d
        self.data = [threshold]


class PMTHighVoltageAdjustMessage(HisparcMessage):
    def __init__(self, channel, voltage = 0x00):
        HisparcMessage.__init__(self)

        if channel is 1 or channel is 2:
            self.identifier = 0x1e + (channel - 1)

        self.data = [voltage]


class ThresholdAdjustMessage(HisparcMessage):
    def __init__(self, channel, low = True, threshold = None):
        HisparcMessage.__init__(self)

        if threshold is None:
            threshold = 0x0100 if low else 0x0800

        if channel is 1:
            self.identifier = 0x20 if low else 0x21
        if channel is 2:
            self.identifier = 0x22 if low else 0x23

        self.data = [((threshold >> 8) & 0xff), (threshold & 0xff)]


class TriggerConditionMessage(HisparcMessage):
    def __init__(self, condition = 0x08):
        HisparcMessage.__init__(self)

        self.identifier = 0x30
        self.data = [condition]


class PreCoincidenceTimeMessage(HisparcMessage):
    def __init__(self, time = 0x00c8):
        HisparcMessage.__init__(self)

        self.identifier = 0x31
        self.data = [((time >> 8) & 0xff), (time & 0xff)]


class CoincidenceTimeMessage(HisparcMessage):
    def __init__(self, time = 0x0190):
        HisparcMessage.__init__(self)

        self.identifier = 0x32
        self.data = [((time >> 8) & 0xff), (time & 0xff)]


class PostCoincidenceTime(HisparcMessage):
    def __init__(self, time = 0x0190):
        HisparcMessage.__init__(self)

        self.identifier = 0x33
        self.data = [((time >> 8) & 0xff), (time & 0xff)]


class InitializeMessage(HisparcMessage):
    def __init__(self, one_second_enabled = True):
        HisparcMessage.__init__(self)

        self.identifier = 0x35
        self.data = [0x00, 0x00, 0x00, 0x03 if one_second_enabled else 0x01]


class ResetMessage(HisparcMessage):
    def __init__(self, confirm = False):
        HisparcMessage.__init__(self)

        self.identifier = 0xff


def HisparcMessageFactory(buff):
    """Return a message, extracted from the buffer

    Inspect the buffer and extract the first full message. A
    HisparcMessage subclass instance will be returned, according to
    the type of the message.

    :param buff: the contents of the usb buffer
    :return: instance of a HisparcMessage subclass

    """
    for cls in HisparcMessage.__subclasses__():
        if cls.is_message_for(buff):
            return cls(buff)
    raise NotImplementedError("Message type not implemented")
