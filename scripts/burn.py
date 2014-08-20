import os.path
import time
import sys

import pylibftdi


SET_BITS_LOW = 0x80
GET_BITS_LOW = 0x81
SET_BITS_HIGH = 0x82
GET_BITS_HIGH = 0x83
TCK_DIVISOR = 0x86
DISABLE_CLK_DIV5 = 0x8A
WRITE_BYTES_PVE_LSB = 0x18


def write(dev, data):
    dev.write(bytearray(data))

def print_high_bits(f):
    write(f, [GET_BITS_HIGH])
    time.sleep(.01)
    print 'high:', [bin(ord(u)) for u in f.read(1)]

def burn(firmware_file):
    f = pylibftdi.Device("HiSPARC III Master", interface_select=1)

    # Select MPSSE mode (0x02)
    # Direction is not used here, it doesn't seem to work.
    # We'll set the direction explicitly later.
    f.ftdi_fn.ftdi_set_bitmode(0, 0x02)

    # Set clock frequency to 30 MHz (0x0000)
    write(f, [TCK_DIVISOR, 0, 0])
    # Disable divide clock frequency by 5
    write(f, [DISABLE_CLK_DIV5])

    # bits 0 and 1 are output that is, bits TCK/SK and TDI/DO, clock and
    # data
    write(f, [SET_BITS_LOW, 0, 0b11])

    print_high_bits(f)
    # pull nCONFIG (low byte bit 0) low
    write(f, [SET_BITS_HIGH, 0, 1])
    print_high_bits(f)
    # pull nCONFIG (low byte bit 0) high
    write(f, [SET_BITS_HIGH, 1, 1])
    print_high_bits(f)

    BUFSIZE = 64 * 1024

    with open(os.path.expanduser(firmware_file), 'rb') as file:
        while True:
            xbuf = file.read(BUFSIZE)
            if not xbuf:
                break

            LENGTH = len(xbuf) - 1
            LENGTH_L = LENGTH & 0xff
            LENGTH_H = LENGTH >> 8 & 0xff
            write(f, [WRITE_BYTES_PVE_LSB, LENGTH_L, LENGTH_H])
            write(f, xbuf)

    print_high_bits(f)


if len(sys.argv) < 2:
    print 'Usage: python burn.py [firmware file]'
else:
    burn(sys.argv[1])
