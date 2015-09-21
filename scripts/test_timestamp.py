import pysparc.hardware
from pysparc import messages

if 'dev' not in globals():
    dev = pysparc.hardware.HiSPARCIII()
    dev.reset_hardware()

dev.config.one_second_enabled = True
while True:
    msg = dev.read_message()
    if (isinstance(msg, messages.OneSecondMessage)):
        print msg.timestamp, msg.count_ticks_PPS, msg.quantization_error
