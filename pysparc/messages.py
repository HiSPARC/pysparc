"""Process HiSPARC hardware messages

Parse and operate on messages from and to the HiSPARC II / III hardware.

:class:`HisparcMessage`: factory class for HiSPARC messages

"""
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


class HisparcMessage(object):

    """HiSPARC Message base/factory class

    Base and factory class for HiSPARC hardware messages.

    """

    def __init__(self, buff):
        raise NotImplementedError("This is a base class. "
                                  "Do not instantiate!")

    @classmethod
    def is_message_for(cls, buff):
        return False


class OneSecondMessage(HisparcMessage):
    def __init__(self, buff):
        pass

    @classmethod
    def is_message_for(cls, buff):
        if ord(buff[1]) == msg_ids['one_second']:
            return True
        else:
            return False
