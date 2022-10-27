import logging
import time

from pysparc.hardware import HiSPARCIII
import pysparc.align_adcs


if __name__ == '__main__':
    reload(pysparc.align_adcs)
    logging.basicConfig(level=logging.DEBUG)

    if 'primary' not in globals():
        primary = HiSPARCIII()
    else:
        primary.reset_hardware()
    if 'secondary' not in globals():
        secondary = HiSPARCIII(secondary=True)
    else:
        secondary.reset_hardware()

    align_adcs = pysparc.align_adcs.AlignADCsPrimarySecondary(primary, secondary)
    align_adcs.align()
    align_adcs = pysparc.align_adcs.AlignADCs(primary)
    align_adcs.align()
    secondary.reset_hardware()
    time.sleep(5)
    align_adcs = pysparc.align_adcs.AlignADCsPrimarySecondary(primary, secondary)
    align_adcs.align()
