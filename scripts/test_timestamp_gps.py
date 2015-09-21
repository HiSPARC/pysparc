import pysparc.hardware
from pysparc import gps_messages

if 'dev' not in globals():
    dev = pysparc.hardware.TrimbleGPS()

while True:
    msg = dev.read_message()
    if (isinstance(msg, gps_messages.SupplementalTimingPacket)):
        print msg.pps_quantization_error
