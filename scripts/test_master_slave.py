import logging

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
    # align_adcs = pysparc.align_adcs.AlignADCs(master)
    try:
        align_adcs.align()
    except Exception as e:
        print e

    print
    print "All master configuration settings:"
    print
    for attr in sorted(master.config.members()):
        print attr, getattr(master.config, attr)
    print
    print
    print "All slave configuration settings:"
    print
    for attr in sorted(slave.config.members()):
        print attr, getattr(slave.config, attr)
    print
