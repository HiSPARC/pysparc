import logging
import time

from pysparc.hardware import HiSPARCII, HiSPARCIII, TrimbleGPS
from pysparc.ftdi_chip import DeviceNotFoundError
from pysparc import gps_messages


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
        t0 = time.time()
        has_reset = False

        # msg = gps_messages.ResetMessage(reset_mode='warm')
        # msg = gps_messages.SetInitialPosition(52, 4, 0)
        # self.gps.send_message(msg)

        try:
            while True:
                if time.time() - t0 > 5 and has_reset is False:
                    msg = gps_messages.ResetMessage('warm')
                    self.gps.send_message(msg)
                    msg = gps_messages.SetSurveyParameters(60)
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
