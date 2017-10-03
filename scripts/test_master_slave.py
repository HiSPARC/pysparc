import logging

from pysparc.hardware import HiSPARCIII
from pysparc.align_adcs import AlignADCsMasterSlave


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    master = HiSPARCIII()
    slave = HiSPARCIII(slave=True)

    align_adcs = AlignADCsMasterSlave(master, slave)
    align_adcs.align()

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
