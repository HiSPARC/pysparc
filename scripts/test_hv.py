from __future__ import division

import logging
import os

from pysparc.hardware import HiSPARCIII
from pysparc.align_adcs import AlignADCs
from pysparc import messages


CONFIGFILE = 'config.ini'


def main():
    hardware = HiSPARCIII()

    try:
        if not os.path.isfile(CONFIGFILE):
            logging.info("No config file found.  Aligning ADCs.")
            align_adcs = AlignADCs(hardware)
            align_adcs.align()
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
        logging.info("Writing config to file")
        hardware.config.write_config(CONFIGFILE)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
