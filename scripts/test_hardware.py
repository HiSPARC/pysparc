from __future__ import division

import logging
import time
import os
from ConfigParser import ConfigParser

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
            config = ConfigParser()
            config.read(CONFIGFILE)
            hardware.config.read_config(config)

        hardware.config.trigger_condition = 0x80
        while True:
            msg = hardware.flush_and_get_measured_data_message()
            print '%d %d %d %d' % (msg.adc_ch1_pos.mean(),
                                   msg.adc_ch1_neg.mean(),
                                   msg.adc_ch2_pos.mean(),
                                   msg.adc_ch2_neg.mean())

            bl1 = msg.trace_ch1[:100].mean()
            bl1_pos = msg.adc_ch1_pos[:50].mean()
            bl1_neg = msg.adc_ch1_neg[:50].mean()
            ph1 = msg.trace_ch1.max()

            bl2 = msg.trace_ch2[:100].mean()
            bl2_pos = msg.adc_ch2_pos[:50].mean()
            bl2_neg = msg.adc_ch2_neg[:50].mean()
            ph2 = msg.trace_ch2.max()

            print "baselines: %d (%d, %d), %d (%d, %d)" % \
                (bl1, bl1_pos, bl1_neg, bl2, bl2_pos, bl2_neg)
            print "pulseheights: %d %d" % (ph1 - bl1, ph2 - bl2)
    except KeyboardInterrupt:
        print "Interrupted by user."
    finally:
        hardware.close()
        hardware.config.set_notifications_enabled(False)
        logging.info("Writing config to file")
        config = ConfigParser()
        hardware.config.write_config(config)
        with open(CONFIGFILE, 'w') as f:
            config.write(f)
        print
        print "All configuration settings:"
        print
        for attr in sorted(hardware.config.members()):
            print attr, getattr(hardware.config, attr)
        print


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
