"""Write timestamp (with nanoseconds) on external trigger

This script was written for a project on gravitational waves.  An ad hoc
timing setup is created for a seismic waves field experiment in Italy
using two PCs separated by up to 600 m, without a network connection.  The
setup uses HiSPARC III hardware with GPS.  This script enables external
trigger mode and writes the timestamp using the logging module.

"""
from __future__ import division

import logging
import time

from hardware import Hardware
import messages


TIMESTAMPS_FILE = 'timestamps.log'


def average(values):
    return sum(values) / len(values)

def main():
    hardware = Hardware()
    with open(TIMESTAMPS_FILE, 'a', buffering=1) as f:
        try:
            # Use external trigger only
            hardware.send_message(messages.TriggerConditionMessage(0b1000000))
            while True:
                msg = hardware.read_message()
                if type(msg) == messages.MeasuredDataMessage:
                    logging.info("%s %s ns", msg.timestamp,
                                 msg.count_ticks_PPS)
                    f.write("%s %s ns\n" % (msg.timestamp,
                            msg.count_ticks_PPS))
        except KeyboardInterrupt:
            print "Interrupted by user."
        finally:
            hardware.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
