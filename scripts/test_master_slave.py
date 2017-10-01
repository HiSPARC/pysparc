from pysparc.hardware import HiSPARCIII
from pysparc.align_adcs import AlignADCs


if __name__ == '__main__':
    master = HiSPARCIII()
    slave = HiSPARCIII(slave=True)

    align_adcs = AlignADCs(master)
    align_adcs.align()
    print
    print "All configuration settings:"
    print
    for attr in sorted(master.config.members()):
        print attr, getattr(master.config, attr)
    print

    align_adcs = AlignADCs(slave)
    align_adcs.align()
    print
    print "All configuration settings:"
    print
    for attr in sorted(slave.config.members()):
        print attr, getattr(slave.config, attr)
    print
