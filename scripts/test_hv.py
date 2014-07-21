from __future__ import division

import logging
import time
import os

from pysparc.hardware import HiSPARCIII
from pysparc.align_adcs import AlignADCs
from pysparc import messages


CONFIGFILE = 'config.ini'


def average(values):
    return sum(values) / len(values)

def main():
    hardware = HiSPARCIII()

    try:
        if not os.path.isfile(CONFIGFILE):
            logging.info("No config file found.  Aligning ADCs.")
            align_adcs = AlignADCs(hardware)
            t0 = time.time()
            align_adcs.align()
            t1 = time.time()
            logging.info("Alignment took %.1f s", t1 - t0)
        else:
            logging.info("Reading config from file")
            hardware.config.read_config(CONFIGFILE)

        hardware.config.ch1_voltage = 800
        hardware.config.ch2_voltage = 800

        # at least two low
        hardware.config.trigger_condition = 0b10
        hardware.send_message(messages.InitializeMessage(
                one_second_enabled=True))

        while True:
            msg = hardware.read_message()
            if msg is not None:
                print msg
    except KeyboardInterrupt:
        print "Interrupted by user."
    finally:
        hardware.close()
        hardware.config.set_notifications_enabled(False)
        logging.info("Writing config to file")
        hardware.config.write_config(CONFIGFILE)
        print
        print "All configuration settings:"
        print
        for attr in sorted(hardware.config.members()):
            print attr, getattr(hardware.config, attr)
        print


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
