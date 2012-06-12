from pyftdi.pyftdi.ftdi import Ftdi
from pyftdi.serialext.ftdiext import SerialFtdi


def main():
    master = find_master()
    if not master:
        raise RuntimeError("HiSPARC III Master not found")
    s = SerialFtdi(master, timeout=3)
    s.write('\x99\x35\x00\x00\x00\x03\x66')
    while True:
        msg = s.read(10000)
        print repr(msg)

def find_master():
    devices = Ftdi.find_all([(0x403, 0x6010)])
    for device in devices:
        vendor_id, product_id, serial_str, num_interfaces, \
            description = device 
        if description == "HiSPARC III Master":
            return "ftdi://ftdi:2232:%s/2" % serial_str
    return None

main()
