from pysparc.hardware import HiSPARCIII

if __name__ == '__main__':
    master = HiSPARCIII()
    slave = HiSPARCIII(slave=True)
