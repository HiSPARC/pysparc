from __future__ import division

import logging
import time

from hardware import Hardware
import messages


def average(values):
    return sum(values) / len(values)

def main():
    hardware = Hardware()
    try:
        hardware.align_adcs()
        hardware.send_message(messages.TriggerConditionMessage(0x80))
        while True:
            msg = hardware.flush_and_get_measured_data_message()
            print '%d %d %d %d' % (msg.adc_ch1_pos.mean(),
                                   msg.adc_ch1_neg.mean(),
                                   msg.adc_ch2_pos.mean(),
                                   msg.adc_ch2_neg.mean())
            bl1 = int(round(msg.trace_ch1[:100].mean()))
            ph1 = msg.trace_ch1.max()
            bl2 = int(round(msg.trace_ch2[:100].mean()))
            ph2 = msg.trace_ch2.max()
            print "baselines:", bl1, bl2
            print "pulseheights:", ph1 - bl1, ph2 - bl2
    except KeyboardInterrupt:
        print "Interrupted by user."
    finally:
        hardware.close()
        print
        print "All configuration settings:"
        print
        for key, value in hardware.config.__dict__.iteritems():
            print key, value['value']
        print


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    main()
