from __future__ import division

import logging
import time

from hardware import Hardware
import messages


def average(values):
    return sum(values) / len(values)

def main():
    hardware = Hardware()
    hardware.align_adcs()
    hardware.send_message(messages.TriggerConditionMessage(0x80))
    while True:
        print hardware._get_mean_adc_value()
    hardware.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
