import logging

from hardware import Hardware


def main():
    hardware = Hardware()
    #while True:
    #    msg = s.read(10000)
    #    print repr(msg)


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    main()
