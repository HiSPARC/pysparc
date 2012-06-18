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
    except KeyboardInterrupt:
        print "Interrupted by user."
    finally:
        hardware.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
