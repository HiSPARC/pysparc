"""Process GPS hardware messages

Parse and operate on messages from and to the Trimble GPS hardware.

:class:`GPSMessage`: factory class for GPS messages

"""

import struct
import logging

from messages import (BaseMessage, MessageError, StartCodonError,
                      CorruptMessageError)


logger = logging.getLogger(__name__)


msg_ids = {'report_superpacket': 0x8f}

superpacket_ids = {'primary_timing': 0xab,
                   'supplemental_timing': 0xac,
                  }

# error_ids = {'header_not_detected': 0x99,
#              'identifier_unknown': 0x89,
#              'stop_codon_not_detected': 0x66,
#              }

# command_ids = {'soft_reset': 0xff,
#                'set_all_controls': 0x50,
#                'get_all_controls': 0x55,
#                }


class GPSMessage(BaseMessage):

    """GPS Message base/factory class

    Base and factory class for GPS hardware messages.

    """
    container_format = '>BB%sH'
    codons = {'start': 0x10, 'stop': 0x1003}


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
    msg_format = '>BB17sH'

    def __init__(self, buff):
        super(PrimaryTimingPacket, self).__init__()
        self.parse_message(buff)

    def parse_message(self, buff):
        msg_length = struct.calcsize(self.msg_format)
        str_buff = str(buff[:msg_length])

        print ','.join([hex(ord(u)) for u in str_buff])

        (header, identifier, msg, end) = \
            struct.unpack_from(self.msg_format, str_buff)

        self.validate_codons_and_id(header, identifier, end)

        del buff[:msg_length]


class SupplementalTimingPacket(ReportSuperPacket):

    sub_identifier = superpacket_ids['supplemental_timing']
    msg_format = '>BB68sH'

    def __init__(self, buff):
        super(SupplementalTimingPacket, self).__init__()
        self.parse_message(buff)

    def parse_message(self, buff):
        msg_length = struct.calcsize(self.msg_format)
        str_buff = str(buff[:msg_length])

        (header, identifier, msg, end) = \
            struct.unpack_from(self.msg_format, str_buff)

        self.validate_codons_and_id(header, identifier, end)

        del buff[:msg_length]


def GPSMessageFactory(buff):
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
