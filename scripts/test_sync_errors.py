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
    master.config.trigger_condition = trigger_one_second
    master.flush_device()

    logging.info(wait_for_message(master))
    print 40 * '-'
    time.sleep(7)

    master.flush_device()

    for i in range(5):
        msg = wait_for_message(master)
        logging.info('%s -- %s' % (time.ctime(), time.ctime(msg.timestamp)))

    master.config.full_scale = 0
    logging.info(wait_for_message(master).trace_ch1.mean())
    master.config.full_scale = 0xff
    logging.info(wait_for_message(master).trace_ch1.mean())
    master.config.full_scale = 0
    logging.info(wait_for_message(master).trace_ch1.mean())
