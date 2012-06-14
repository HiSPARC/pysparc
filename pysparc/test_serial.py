import logging

from hardware import Hardware
import messages


def main():
    hardware = Hardware()
    hardware.send_message(messages.TriggerConditionMessage(0x80))
    while True:
        msg = hardware.read_message()
        print msg


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
