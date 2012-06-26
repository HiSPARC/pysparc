from __future__ import division

import logging
import time

from hardware import Hardware
from align_adcs import AlignADCs
import messages


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

        hardware.send_message(messages.TriggerConditionMessage(1))
        while True:
            t0 = time.time()
            count = 0
            while time.time() - t0 < 1.:
                msg = hardware.read_message()
                if type(msg) == messages.MeasuredDataMessage:
                    count += 1
            print "Frequency: %.1f" % (count / (time.time() - t0))
    except KeyboardInterrupt:
        print "Interrupted by user."
    finally:
        hardware.close()
        print
        print "All configuration settings:"
        print
        for key, value in sorted(hardware.config.__dict__.iteritems()):
            print key, value['value']
        print


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
