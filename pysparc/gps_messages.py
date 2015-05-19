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


msg_ids = {'report_superpacket': 0x8f}

superpacket_ids = {'primary_timing': 0xab,
                   'supplemental_timing': 0xac,
                  }

# Match ETX and all directly preceding DLEs, per the Trimble manual.
stop_codon_pattern = re.compile('\x10+\x03')


class GPSMessage(BaseMessage):

    """GPS Message base/factory class

    Base and factory class for GPS hardware messages.

    """
    container_format = '>BB%sH'
    codons = {'start': 0x10, 'stop': 0x1003}

    @classmethod
    def extract_message_from_buffer(cls, buff):
        idx = None
        # If the number of DLEs is even, they are effectively all escaped and
        # are not part of the stop codon. If the number is odd, the final one
        # is *not* escaped, and is part of the stop codon.
        for match in stop_codon_pattern.finditer(buff):
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


class ReportSuperPacket(GPSMessage):

    """TSIP super packet

    The Trimble GPS documentation defines so-called superpackets as an extension
    to regular TSIP. These superpackets allow a class of packets to share the
    same identifier. Identifying the precise packet is done using a
    sub-identifier.

    """

    identifier = msg_ids['report_superpacket']
    sub_identifier = None

    @classmethod
    def is_message_for(cls, buff):
        if len(buff) < 3:
            return False
        else:
            cls.validate_message_start(buff)
            if buff[1] == cls.identifier and buff[2] == cls.sub_identifier:
                return True
            else:
                return False


class PrimaryTimingPacket(ReportSuperPacket):

    sub_identifier = superpacket_ids['primary_timing']
    msg_format = '>BBBIHhB5BHH'

    def __init__(self, buff):
        super(PrimaryTimingPacket, self).__init__()
        self.parse_message(buff)

    def parse_message(self, buff):
        logger.warning("FIXME, don't search for messages")
        idx = None
        # If the number of DLEs is even, they are effectively all escaped and
        # are not part of the stop codon. If the number is odd, the final one is
        # *not* escaped, and is part of the stop codon.
        for match in stop_codon_pattern.finditer(buff):
            group = match.group()
            if (group.count('\x10') % 2 == 1):
                idx = match.end()
                break
        if idx:
            msg = str(buff[:idx])
            str_buff = msg.replace('\x10\x10', '\x10')

        (header, identifier, sub_identifier, self.time_of_week,
         self.week_number, self.utc_offset, self.timing_flag, self.seconds,
         self.minutes, self.hours, self.day_of_month, self.month, self.year,
         end) = \
            struct.unpack_from(self.msg_format, str_buff)

        self.validate_codons_and_id(header, identifier, end)

        del buff[:idx]

    def __str__(self):
        return 'Primary Timing Packet: %d-%d-%d %d:%02d:%02d' % (
            self.year, self.month, self.day_of_month, self.hours, self.minutes,
            self.seconds)


class SupplementalTimingPacket(ReportSuperPacket):

    sub_identifier = superpacket_ids['supplemental_timing']
    msg_format = '>BB68sH'

    def __init__(self, buff):
        super(SupplementalTimingPacket, self).__init__()
        self.parse_message(buff)

    def parse_message(self, buff):
        logger.warning("FIXME, don't search for messages")
        idx = None
        for match in stop_codon_pattern.finditer(buff):
            group = match.group()
            if (group.count('\x10') % 2 == 1):
                idx = match.end()
                break
        if idx:
            msg = str(buff[:idx])
            str_buff = msg.replace('\x10\x10', '\x10')

        (header, identifier, msg, end) = \
            struct.unpack_from(self.msg_format, str_buff)

        self.validate_codons_and_id(header, identifier, end)

        del buff[:idx]


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


def OldGPSMessageFactory(buff):
    """Return a message, extracted from the buffer

    Inspect the buffer and extract the first full message. A
    GPSMessage subclass instance will be returned, according to
    the type of the message.

    :param buff: the contents of the usb buffer
    :return: instance of a GPSMessage subclass

    """
    while True:
        try:
            GPSMessage.validate_message_start(buff)
        except StartCodonError:
            logger.warning("Start codon error, stripping buffer.")
            GPSMessage.strip_until_start_codon(buff)
        except IndexError:
            return None
        else:
            break

    for cls in GPSMessage.__subclasses__() + ReportSuperPacket.__subclasses__():
        if cls.is_message_for(buff):
            try:
                return cls(buff)
            except CorruptMessageError:
                logger.warning("Corrupt message, stripping buffer.")
                GPSMessage.strip_partial_message(buff)
                return GPSMessageFactory(buff)
            except struct.error:
                # message is too short, wait for the rest to come in.
                logger.debug("Message is too short, wait for more data.")
                return None
            except ValueError:
                # some value in a message could not be converted.
                # Probably a corrupt message
                logger.warning("ValueError, so probably a corrupt message; "
                               "stripping buffer.")
                GPSMessage.strip_partial_message(buff)
                return GPSMessageFactory(buff)

    # Unknown message type.  This usually happens after a partial or
    # corrupt message is stripped away until a new start codon is found.
    # This 'start codon' is probably not an actual start codon, but
    # somewhere in the middle of a partial message.
    if (len(buff) >= 2):
        logger.warning("Unknown message type: %x (corrupt?), "
                       "stripping buffer." % buff[1])
    else:
        logger.warning("Corrupt message, stripping buffer.")
    GPSMessage.strip_partial_message(buff)
    return GPSMessageFactory(buff)
