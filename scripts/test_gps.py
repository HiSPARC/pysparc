import logging

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
        try:
            while True:
                msg = self.gps.read_message()
                if msg:
                    print msg

        except KeyboardInterrupt:
            logging.info("Keyboard interrupt, shutting down.")

        return self.gps._buffer


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    app = Main()
    buff = app.run()
    app.close()
