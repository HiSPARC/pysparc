import logging
import time

from pysparc.hardware import HiSPARCIII
import pysparc.align_adcs


if __name__ == '__main__':
    reload(pysparc.align_adcs)
    logging.basicConfig(level=logging.DEBUG)

    if 'master' not in globals():
        master = HiSPARCIII()
    else:
        master.reset_hardware()
    if 'slave' not in globals():
        slave = HiSPARCIII(slave=True)
    else:
        slave.reset_hardware()

    align_adcs = pysparc.align_adcs.AlignADCsMasterSlave(master, slave)
    align_adcs.align()
    align_adcs = pysparc.align_adcs.AlignADCs(master)
    align_adcs.align()
    slave.reset_hardware()
    time.sleep(5)
    align_adcs = pysparc.align_adcs.AlignADCsMasterSlave(master, slave)
    align_adcs.align()
