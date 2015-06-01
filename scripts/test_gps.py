import logging
import time

from pysparc.hardware import HiSPARCII, HiSPARCIII, TrimbleGPS
from pysparc.ftdi_chip import DeviceNotFoundError
from pysparc import gps_messages


class Main(object):

    def __init__(self):
        # try:
        #     self.device = HiSPARCIII()
        # except DeviceNotFoundError:
        #     self.device = HiSPARCII()
        self.gps = TrimbleGPS()

    def close(self):
        logging.info("Closing down")
        # self.device.close()
        self.gps.close()

    def run(self):
        t0 = t1 = time.time()
        has_reset = False

        # msg = gps_messages.ResetMessage(reset_mode='warm')
        # msg = gps_messages.SetInitialPosition(52, 4, 0)
        # self.gps.send_message(msg)

        try:
            while True:
                if time.time() - t1 > 1:
                    t1 = time.time()
                    self.gps._device.write('\x10\xbb\x00\x10\x03')

                if time.time() - t0 > 5 and has_reset is False:
                    msg = gps_messages.ResetMessage('factory')
                    self.gps.send_message(msg)
                    time.sleep(2.2)
                    msg = gps_messages.SetSurveyParameters(86400)
                    self.gps.send_message(msg)
                    has_reset = True

                msg = self.gps.read_message()
                if msg:
                    print msg
                if type(msg) == gps_messages.SupplementalTimingPacket:
                    print "Survey status: %d%%" % msg.survey_progress
                    print "Lat: %f, Lon: %f, Alt: %f" % (msg.latitude,
                                                         msg.longitude,
                                                         msg.altitude)
        except KeyboardInterrupt:
            logging.info("Keyboard interrupt, shutting down.")

        return self.gps._buffer


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    app = Main()
    buff = app.run()
    app.close()
