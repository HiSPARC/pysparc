import time

from pysparc.hardware import HiSPARCIII, TrimbleGPS
from pysparc.messages import MeasuredDataMessage, OneSecondMessage
from pysparc.gps_messages import PrimaryTimingPacket


if __name__ == '__main__':
    gps = TrimbleGPS()
    hisparc = HiSPARCIII()

    hisparc.config.ch1_voltage = 900
    hisparc.config.ch1_threshold_low = 1000
    hisparc.config.trigger_condition = 1
    hisparc.config.one_second_enabled = True

    while True:
        msg = hisparc.read_message()
        if type(msg) == MeasuredDataMessage:
            print msg.gps_seconds
        if type(msg) == OneSecondMessage:
            print "ONE:", msg.gps_seconds
        msg = gps.read_message()
        if type(msg) == PrimaryTimingPacket:
            print "GPS:", msg.seconds
