"""Process GPS hardware messages

Parse and operate on messages from and to the Trimble GPS hardware.

:class:`GPSMessage`: factory class for GPS messages

"""

import struct
import logging
import re

from messages import (BaseMessage, MessageError, StartCodonError,
                      CorruptMessageError)


logger = logging.getLogger(__name__)


msg_ids = {'primary_timing': 0x8fab,
           'supplemental_timing': 0x8fac,
           }

class GPSMessage(BaseMessage):

    """GPS Message base/factory class

    Base and factory class for GPS hardware messages.

    """
    container_format = '>BB%sH'
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
        return msg.startswith(cls.identifier)


class PrimaryTimingPacket(GPSMessage):

    identifier = msg_ids['primary_timing']
    msg_format = '>HIHhB5BH'

    def __init__(self, msg):
        super(PrimaryTimingPacket, self).__init__()
        self.parse_message(msg)

    def parse_message(self, msg):
        (identifier, self.time_of_week, self.week_number, self.utc_offset,
         self.timing_flag, self.seconds, self.minutes, self.hours,
         self.day_of_month, self.month, self.year) = \
            struct.unpack(self.msg_format, msg)

    def __str__(self):
        return 'Primary Timing Packet: %d-%d-%d %d:%02d:%02d' % (
            self.year, self.month, self.day_of_month, self.hours, self.minutes,
            self.seconds)


class SupplementalTimingPacket(GPSMessage):

    identifier = msg_ids['supplemental_timing']
    msg_format = '>H68sH'

    def __init__(self, msg):
        super(SupplementalTimingPacket, self).__init__()
        self.parse_message(msg)

    def parse_message(self, msg):
        (identifier, msg, end) = \
            struct.unpack(self.msg_format, msg)


def GPSMessageFactory(buff):
    """Return a message, extracted from the buffer

    Inspect the buffer and extract the first full message. A
    GPSMessage subclass instance will be returned, according to
    the type of the message.

    :param buff: the contents of the usb buffer
    :return: instance of a GPSMessage subclass

    """
    msg = GPSMessage.extract_message_from_buffer(buff)
    cls = find_message_class(msg, GPSMessage)
    return cls(msg)


def find_message_class(msg, cls):
    """Return the class implementing the correct message type.

    Loop through all subclasses of :param cls: and find the one that implements
    the message type of :param msg:.

    :param msg: a single raw message
    :param cls: the parent class implementing the message types.

    """
    pass
