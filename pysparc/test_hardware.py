from __future__ import division

import logging
import time

from hardware import Hardware
import messages


def average(values):
    return sum(values) / len(values)

def main():
    hardware = Hardware()
    hardware.send_message(messages.TriggerConditionMessage(0x80))
    hardware.send_message(messages.FullScaleAdjustHisparcMessage(0x80))
    while True:
        msg = hardware.read_message()
        print msg
        if type(msg) == messages.MeasuredDataMessage:
            print average(msg.trace_ch1), msg.trace_ch1[:10]
            print average(msg.trace_ch2), msg.trace_ch2[:10]
            print len(msg.trace_ch1), len(msg.trace_ch2)
    hardware.close()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
