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
            print hardware._get_mean_adc_value()
    except KeyboardInterrupt:
        print "Interrupted by user."
    finally:
        hardware.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
