import logging
import time

from pysparc.hardware import HiSPARCIII
from pysparc.config import Config

logging.basicConfig(level=logging.INFO)



# def wait_for_message(device):
#     msg = None
#     while msg is None:
#         msg = device.read_message()
#     return msg

def wait_for_message(device):
    return device.flush_and_get_measured_data_message()


if __name__ == '__main__':
    trigger_one_second = Config.build_trigger_condition(calibration_mode=True)
    trigger_none = Config.build_trigger_condition(use_external=True)

    primary = HiSPARCIII()
    secondary = HiSPARCIII(secondary=True)
    primary.config.trigger_condition = trigger_one_second
    primary.flush_device()
    secondary.flush_device()

    while True:
        msg = primary.read_message()
        if msg:
            logging.info('PRIMARY   %s -- %s PRIMARY' % (msg.datetime, msg.nanoseconds))
        msg = secondary.read_message()
        if msg:
            logging.info('SECONDARY %s -- %s SECONDARY' % (msg.datetime, msg.nanoseconds))
