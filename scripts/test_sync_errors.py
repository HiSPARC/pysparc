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

    master = HiSPARCIII()
    slave = HiSPARCIII(slave=True)
    master.config.trigger_condition = trigger_one_second
    master.flush_device()
    slave.flush_device()

    while True:
        msg = master.read_message()
        if msg:
            logging.info('MASTER %s -- %s MASTER' % (msg.datetime, msg.nanoseconds))
        msg = slave.read_message()
        if msg:
            logging.info('SLAVE  %s -- %s SLAVE' % (msg.datetime, msg.nanoseconds))
