"""Process GPS hardware messages

Parse and operate on messages from and to the Trimble GPS hardware.

:class:`GPSMessage`: factory class for GPS messages

"""

import struct
import logging

from messages import (HisparcMessage, MessageError, StartCodonError,
                      CorruptMessageError)


logger = logging.getLogger(__name__)


codons = {'start': 0x10, 'stop': 0x1003}

# msg_ids = {'measured_data': 0xa0,
#            'comparator_data': 0xa2,
#            'one_second': 0xa4,
#            'all_controls': 0x55,
#            'communication_error': 0x88,
#            'reset': 0xff,
#            }

# error_ids = {'header_not_detected': 0x99,
#              'identifier_unknown': 0x89,
#              'stop_codon_not_detected': 0x66,
#              }

# command_ids = {'soft_reset': 0xff,
#                'set_all_controls': 0x50,
#                'get_all_controls': 0x55,
#                }


class GPSMessage(HisparcMessage):

    """GPS Message base/factory class

    Base and factory class for GPS hardware messages.

    """
    container_format = '>BB%sH'


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
            strip_until_start_codon(buff)
        except IndexError:
            return None
        else:
            break

    for cls in GPSMessage.__subclasses__():
        if cls.is_message_for(buff):
            try:
                return cls(buff)
            except CorruptMessageError:
                logger.warning("Corrupt message, stripping buffer.")
                strip_partial_message(buff)
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
                strip_partial_message(buff)
                return GPSMessageFactory(buff)

    # Unknown message type.  This usually happens after a partial or
    # corrupt message is stripped away until a new start codon is found.
    # This 'start codon' is probably not an actual start codon, but
    # somewhere in the middle of a partial message.
    logger.warning("Unknown message type (probably corrupt), "
                   "stripping buffer.")
    strip_partial_message(buff)
    return GPSMessageFactory(buff)


def strip_until_start_codon(buff):
    """Strip bytes from left until start codon is found.

    This method assumes that the data at the start of the buffer is
    actually somewhere in the middle of a message.

    :param buff: the contents of the usb buffer

    """
    try:
        index = buff.index(chr(codons['start']))
    except ValueError:
        del buff[:]
    else:
        del buff[:index]


def strip_partial_message(buff):
    """Strip partial message from left, until new start codon found.

    This method assumes that there is a message in the buffer, but that
    it is only a partial message.  Strip data until a new message appears
    to begin.

    :param buff: the contents of the usb buffer

    """
    del buff[0]
    return strip_until_start_codon(buff)
