import os.path
import time

from pyftdi.pyftdi.ftdi import Ftdi, FtdiError
from pyftdi.pyftdi.spi import SpiController
import usb

from array import array as Array

def print_low_bits(f):
    f.write_data([Ftdi.GET_BITS_LOW])
    time.sleep(.01)
    print 'low: ', [bin(ord(u)) for u in f.read_data(1)]

def print_high_bits(f):
    f.write_data([Ftdi.GET_BITS_HIGH])
    time.sleep(.01)
    print 'high:', [bin(ord(u)) for u in f.read_data(1)]

def burn():
    global f
    f = Ftdi()
    try:
        f.open_mpsse(0x0403, 0x6010, 1, initial=1, direction=0b11)
    except (FtdiError, usb.USBError):
        print "RESET"
        usb.util.dispose_resources(f.usb_dev)
        f.open_mpsse(0x0403, 0x6010, 1, initial=1, direction=0b11)

    f.write_data([Ftdi.TCK_DIVISOR, 0, 0])
    f.write_data([Ftdi.DISABLE_CLK_DIV5])

    print_low_bits(f)

    print_high_bits(f)
    f.write_data([Ftdi.SET_BITS_HIGH, 0, 1])
    print_high_bits(f)
    f.write_data([Ftdi.SET_BITS_HIGH, 1, 1])
    print_high_bits(f)

    BUFSIZE = 32 * 1024

    time.sleep(1)

    with open(os.path.expanduser('/Users/david/Downloads/FPGAConfig_v19.rbf'), 'rb') as file:
        while True:
            xbuf = file.read(BUFSIZE)
            if not xbuf:
                break
      
            LENGTH = len(xbuf) - 1
            LENGTH_L = LENGTH & 0xff
            LENGTH_H = LENGTH >> 8 & 0xff
            send_buf = [Ftdi.WRITE_BYTES_PVE_LSB] + [LENGTH_L, LENGTH_H] + [ord(u) for u in xbuf]
            f.write_data(send_buf)

    #for i in range(10):
    #    print_high_bits(f)
    #    f.write_data([0x8e, 0])

    print_high_bits(f)
    time.sleep(1)
    print_high_bits(f)
    print_low_bits(f)


burn()
