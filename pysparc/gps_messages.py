"""Process GPS hardware messages

Parse and operate on messages from and to the Trimble GPS hardware.

:class:`GPSMessage`: factory class for GPS messages

"""

import struct
import logging
import re
from math import degrees, radians

from messages import BaseMessage, MessageError, CorruptMessageError


logger = logging.getLogger(__name__)


msg_ids = {'unparsable_packet': 0x13,
           'reset': 0x1e,
           'set_initial_position': 0x32,
           'software_version': 0x45,
           'set_survey_parameters': 0x8ea9,
           'primary_timing': 0x8fab,
           'supplemental_timing': 0x8fac,
           }


class UnknownMessageError(MessageError):

    pass


class GPSMessage(BaseMessage):

    """GPS Message base/factory class

    Base and factory class for GPS hardware messages.

    """
    container_format = '>B%sH'
    codons = {'start': 0x10, 'stop': 0x1003}

    # Match ETX and all directly preceding DLEs, per the Trimble manual.
    stop_codon_pattern = re.compile('\x10+\x03')

    @classmethod
    def extract_message_from_buffer(cls, buff):
        """Extract a single message from the buffer."""

        if not buff.startswith('\x10'):
            try:
                idx = buff.index('\x10')
            except ValueError:
                return None
            else:
                logger.warning("Garbage found, stripping buffer.")
                del buff[:idx]

        # If the number of DLEs is even, they are effectively all escaped and
        # are not part of the stop codon. If the number is odd, the final one
        # is *not* escaped, and is part of the stop codon.
        for match in cls.stop_codon_pattern.finditer(buff):
            # we found something that looks like a stop codon
            group = match.group()
            if (group.count('\x10') % 2 == 1):
                # number of DLEs (first byte of stop codon) is odd
                idx = match.end()
                # this is the message, without the codons
                msg = str(buff[1:idx - 2])
                # remove message from buffer
                del buff[:idx]
                # squash escaped \x10 characters
                msg = msg.replace('\x10\x10', '\x10')
                return msg

    @classmethod
    def is_message_for(cls, msg):
        """Check if this class can decode a particular message.

        :param msg: the message
        :return: True if this class can handle the message. False otherwise.

        """
        if cls.identifier is None:
            return False
        elif cls.identifier <= 0xff:
            return msg.startswith(chr(cls.identifier))
        else:
            return msg.startswith(struct.pack('>H', cls.identifier))

    def encode(self):
        """Encode message to bytestream to be sent to the hardware.

        For GPS messages, the identifier may be a byte or a word. If
        :attr:`msg_format` is the empty string, autodetect the identifier size.

        """
        if self.msg_format == '':
            if self.identifier <= 0xff:
                self.msg_format = 'B'
            else:
                self.msg_format = 'H'
        return super(GPSMessage, self).encode()


class PrimaryTimingPacket(GPSMessage):

    identifier = msg_ids['primary_timing']
    msg_format = '>HIHhB5BH'

    def __init__(self, msg):
        super(PrimaryTimingPacket, self).__init__()
        self.parse_message(msg)

    def parse_message(self, msg):
        try:
            (identifier, self.time_of_week, self.week_number, self.utc_offset,
             self.timing_flag, self.seconds, self.minutes, self.hours,
             self.day_of_month, self.month, self.year) = \
                struct.unpack(self.msg_format, msg)
        except struct.error:
            raise CorruptMessageError("Error unpacking message: %r" % msg)

    def __str__(self):
        return 'Primary Timing Packet: %d-%d-%d %d:%02d:%02d' % (
            self.year, self.month, self.day_of_month, self.hours, self.minutes,
            self.seconds)


class SupplementalTimingPacket(GPSMessage):

    identifier = msg_ids['supplemental_timing']
    msg_format = '>H3BI2H4B2fI2f3df4s'

    def __init__(self, msg):
        super(SupplementalTimingPacket, self).__init__()
        self.parse_message(msg)

    def parse_message(self, msg):
        try:
            (identifier, self.receiver_mode, x1, self.survey_progress, x2, x3,
             self.alarms, self.gps_status, x4, spare1, spare2, self.clock_bias,
             self.clock_bias_rate, x5, x6, self.temperature, self.latitude,
             self.longitude, self.altitude, self.pps_quantization_error,
             spare3) = struct.unpack(self.msg_format, msg)
        except struct.error:
            raise CorruptMessageError("Error unpacking message: %r" % msg)

        self.latitude = degrees(self.latitude)
        self.longitude = degrees(self.longitude)

    def __str__(self):
        return "Supplemental Timing Packet: mode: %d, alarms: %s, " \
               "status: %d" % (self.receiver_mode, bin(self.alarms),
                               self.gps_status)


class ResetMessage(GPSMessage):

    """Reset the Trimble GPS hardware.

    There are four different reset modes; this message implements three of
    them: warm, cold and factory reset. A warm reset will clear the RAM but
    keep all GPS data. A cold reset (equivalent to a power cycle) will clear
    the RAM including the GPS data. The data is read back to RAM from the flash
    ROM. A factory reset will clear the RAM, *and* the flash ROM.

    Interestingly, once the reset is complete, the cold reset appears to have
    kept the GPS location, but not the GPS time. That is set to 1999-8-22. In
    contrast, the factory reset appears to have reset the GPS location (it is
    set to 0., 0., 0.) but the GPS time is retained.

    :param reset_mode: either 'warm', 'cold', or 'factory' (default).

    """

    identifier = msg_ids['reset']
    msg_format = 'BB'

    def __init__(self, reset_mode='warm'):
        super(ResetMessage, self).__init__()

        if reset_mode == 'factory':
            self.data.append(0x46)
        elif reset_mode == 'cold':
            self.data.append(0x4b)
        elif reset_mode == 'warm':
            self.data.append(0x0e)
        else:
            raise ValueError("Unknown reset mode: %s" % reset_mode)


class UnparsablePacket(GPSMessage):

    identifier = msg_ids['unparsable_packet']

    def __init__(self, msg):
        super(UnparsablePacket, self).__init__()
        self.parse_message(msg)

    def parse_message(self, msg):
        self.unparsable_msg = msg

    def __str__(self):
        return "Unparsable Packet: %r" % self.unparsable_msg


class SoftwareVersionMessage(GPSMessage):

    identifier = msg_ids['software_version']
    msg_format = '11B'

    def __init__(self, msg):
        super(SoftwareVersionMessage, self).__init__()
        self.parse_message(msg)

    def parse_message(self, msg):
        try:
            (identifier, self.version_major, self.version_minor,
             self.version_month, self.version_day, self.version_year,
             self.revision_major, self.revision_minor, self.revision_month,
             self.revision_day, self.revision_year) = \
                struct.unpack(self.msg_format, msg)
        except struct.error:
            raise CorruptMessageError("Error unpacking message: %r" % msg)

    def __str__(self):
        return "Firmware version: %d.%d. GPS revision: %d.%d" % \
            (self.version_major, self.version_minor, self.revision_major,
             self.revision_minor)


class SetInitialPosition(GPSMessage):

    identifier = msg_ids['set_initial_position']
    msg_format = 'B3f'

    def __init__(self, latitude, longitude, altitude):
        super(SetInitialPosition, self).__init__()
        latitude = radians(latitude)
        longitude = radians(longitude)
        self.data.extend([latitude, longitude, altitude])


class SetSurveyParameters(GPSMessage):

    identifier = msg_ids['set_survey_parameters']
    msg_format = 'H2B2I'

    def __init__(self, num_fixes=86400):
        super(SetSurveyParameters, self).__init__()
        # enable survey, save position, number of fixes, reserved
        self.data.extend([1, 1, num_fixes, 0])


def GPSMessageFactory(buff):
    """Return a message, extracted from the buffer

    Inspect the buffer and extract the first full message. A
    GPSMessage subclass instance will be returned, according to
    the type of the message.

    :param buff: the contents of the usb buffer
    :return: instance of a GPSMessage subclass

    """
    msg = GPSMessage.extract_message_from_buffer(buff)
    if msg:
        try:
            klass = find_message_class(msg, GPSMessage)
        except UnknownMessageError as e:
            logger.error(e)
            return None
        else:
            try:
                return klass(msg)
            except CorruptMessageError as exc:
                logger.error(exc)
                return None
    else:
        return None


def find_message_class(msg, cls):
    """Return the class implementing the correct message type.

    Loop through all subclasses of :param cls: and find the one that implements
    the message type of :param msg:.

    :param msg: a single raw message
    :param cls: the parent class implementing the message types.
    :return: the class implementing the correct message type.

    """
    for klass in cls.__subclasses__():
        if klass.is_message_for(msg):
            return klass
    raise UnknownMessageError("Unknown message: %r" % msg[:5])
