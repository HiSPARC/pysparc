import logging
import re
import struct
import time

from pysparc.hardware import HiSPARCII, HiSPARCIII, TrimbleGPS
from pysparc.ftdi_chip import DeviceNotFoundError


class Main(object):

    def __init__(self):
        try:
            self.device = HiSPARCIII()
        except DeviceNotFoundError:
            self.device = HiSPARCII()
        self.gps = TrimbleGPS()

    def close(self):
        logging.info("Closing down")
        self.device.close()

    def run(self):
        pattern = re.compile('\x10+\x03')

        try:
            while True:
                msg = self.gps.read_message()
                if msg:
                    print msg

                # self.gps.read_into_buffer()
                # idx = None
                # msg = ''
                # for match in pattern.finditer(self.gps._buffer):
                #     group = match.group()
                #     if (group.count('\x10') % 2 == 1):
                #         idx = match.end()
                #         break
                # if idx:
                #     msg = str(self.gps._buffer[:idx])
                #     del self.gps._buffer[:idx]
                #     msg2 = msg.replace('\x10\x10', '\x10')
                #
                # if msg[:3] == '\x10\x8f\xab':
                #     print '%r ... %r %d %d %d' % (msg[:3], msg[-2:], len(msg), len(msg2), msg.count('\x10'))
                #     if len(msg2) == 21:
                #         tow, week, offset = struct.unpack_from('>LHh', msg[3:])
                #         print tow, week, offset

                # if len(self.gps._buffer) > 4096:
                #     break
                # time.sleep(.1)
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt, shutting down.")

        return self.gps._buffer


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    app = Main()
    buff = app.run()
    app.close()
