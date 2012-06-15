import logging

from hardware import Hardware
import messages


def main():
    hardware = Hardware()
    hardware.send_message(messages.TriggerConditionMessage(0x80))
    hardware.send_message(messages.FullScaleAdjustHisparcMessage(0x80))
    while True:
        msg = hardware.read_message()
        print msg
        if type(msg) == messages.MeasuredDataMessage:
            print msg.trace_ch1[:10]
            print msg.trace_ch2[:10]
            print len(msg.trace_ch1), len(msg.trace_ch2)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
