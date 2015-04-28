import logging
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
        try:
            while True:
                self.gps.read_message()
                time.sleep(1)
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt, shutting down.")


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    app = Main()
    app.run()
    app.close()
