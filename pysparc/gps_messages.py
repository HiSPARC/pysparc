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
