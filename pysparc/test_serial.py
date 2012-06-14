import logging

from hardware import Hardware


def main():
    hardware = Hardware()
    while True:
        msg = hardware.read_message()
        print msg


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
