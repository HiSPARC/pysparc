from struct import Struct


class Message(object):
    def __init__(self):
        self.identifier = None
        self.info = []
        self.data = []

    def encode(self):
        if None is self.identifier:
            return ''

        format = ('2B%(info)ds%(data)dsB' %
                  {'info': len(str(bytearray(self.info))),
                   'data': len(str(bytearray(self.data)))})
        packer = Struct(format)

        return packer.pack(0x99, self.identifier, str(bytearray(self.info)),
                           str(bytearray(self.data)), 0x66)


class ChannelOffsetAdjustMessage(Message):
    def __init__(self, channel, positive = True, offset = 0x80):
        Message.__init__(self)

        if 1 is channel:
            self.identifier = 0x10 if positive else 0x11
        if 2 is channel:
            self.identifier = 0x12 if positive else 0x13

        self.data = [offset]


class ChannelGainAdjustMessage(Message):
    def __init__(self, channel, positive = True, gain = 0x80):
        Message.__init__(self)

        if 1 is channel:
            self.identifier = 0x14 if positive else 0x15
        if 2 is channel:
            self.identifier = 0x16 if positive else 0x17

        self.data = [gain]


class CommonOffsetAdjustMessage(Message):
    def __init__(self, offset = 0x00):
        Message.__init__(self)

        self.identifier = 0x18
        self.data = [offset]


class FullScaleAdjustMessage(Message):
    def __init__(self, scale = 0x00):
        Message.__init__(self)

        self.identifier = 0x19
        self.data = [scale]


class IntergratorTimeAdjustMessage(Message):
    def __init__(self, channel, time = 0xff):
        Message.__init__(self)

        if channel is 1 or channel is 2:
            self.identifier = 0x1a + (channel - 1)

        self.data = [time]


class ComperatorThresholdLowMessage(Message):
    def __init__(self, low = True, threshold = None):
        Message.__init__(self)

        if None is threshold:
            threshold = 0x58 if low else 0xe6

        self.identifier = 0x1c if low else 0x1d
        self.data = [threshold]


class PMTHighVoltageAdjustMessage(Message):
    def __init__(self, channel, voltage = 0x00):
        Message.__init__(self)

        if channel is 1 or channel is 2:
            self.identifier = 0x1e + (channel - 1)

        self.data = [voltage]


class ThresholdAdjustMessage(Message):
    def __init__(self, channel, low = True, threshold = None):
        Message.__init__(self)

        if threshold is None:
            threshold = 0x0100 if low else 0x0800

        if channel is 1:
            self.identifier = 0x20 if low else 0x21
        if channel is 2:
            self.identifier = 0x22 if low else 0x23

        self.data = [((threshold >> 8) & 0xff), (threshold & 0xff)]


class TriggerConditionMessage(Message):
    def __init__(self, condition = 0x08):
        Message.__init__(self)

        self.identifier = 0x30
        self.data = [condition]


class PreCoincidenceTimeMessage(Message):
    def __init__(self, time = 0x00c8):
        Message.__init__(self)

        self.identifier = 0x31
        self.data = [((time >> 8) & 0xff), (time & 0xff)]


class CoincidenceTimeMessage(Message):
    def __init__(self, time = 0x0190):
        Message.__init__(self)

        self.identifier = 0x32
        self.data = [((time >> 8) & 0xff), (time & 0xff)]


class PostCoincidenceTime(Message):
    def __init__(self, time = 0x0190):
        Message.__init__(self)

        self.identifier = 0x33
        self.data = [((time >> 8) & 0xff), (time & 0xff)]


class InitializeMessage(Message):
    def __init__(self, one_second_enabled = True):
        Message.__init__(self)

        self.identifier = 0x35
        self.data = [0x00, 0x00, 0x00, 0x03 if one_second_enabled else 0x01]


class ResetMessage(Message):
    def __init__(self, confirm = False):
        Message.__init__(self)

        self.identifier = 0xff
