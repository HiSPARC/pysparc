import logging
import re
import time

from pysparc.hardware import HiSPARCII, HiSPARCIII, TrimbleGPS


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
                # print self.gps.read_message()
                self.gps.read_into_buffer()
                idx = None
                for match in pattern.finditer(self.gps._buffer):
                    group = match.group()
                    if (group.count('\x10') % 2 == 1):
                        idx = match.end()
                        break
                if idx:
                    msg = self.gps._buffer[:idx]
                    del self.gps._buffer[:idx]
                    msg = msg.replace('\x10\x10', '\x10')
                    print '%r ... %r %d' % (msg[:3], msg[-2:], len(msg))

                # if len(self.gps._buffer) > 4096:
                #     break
                # time.sleep(.1)
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt, shutting down.")

        return self.gps._buffer


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    app = Main()
    buff = app.run()
    app.close()
