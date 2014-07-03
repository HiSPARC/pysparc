from __future__ import division

import logging
import time

from pysparc.hardware import Hardware
from pysparc.align_adcs import AlignADCs
from pysparc import messages


def average(values):
    return sum(values) / len(values)

def main():
    hardware = Hardware()
    align_adcs = AlignADCs(hardware)
    try:
        t0 = time.time()
        align_adcs.align()
        t1 = time.time()
        logging.info("Alignment took %.1f s", t1 - t0)

        count = 0
        total_count = 0
        wait_seconds = 0
        hardware.send_message(messages.TriggerConditionMessage(1))
        while True:
            t0 = time.time()
            total_count += count
            count = 0
            while time.time() - t0 < 1.:
                msg = hardware.read_message()
                if type(msg) == messages.MeasuredDataMessage:
                    count += 1
            print "Frequency: %.1f" % (count / (time.time() - t0))
            if count == 0:
                wait_seconds += 1
            else:
                wait_seconds = 0
            if wait_seconds == 2 and total_count:
                print "I received a total of %d messages" % total_count
                total_count = 0
    except KeyboardInterrupt:
        print "Interrupted by user."
    finally:
        hardware.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
