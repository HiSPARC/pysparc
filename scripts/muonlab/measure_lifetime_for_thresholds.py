import time
import logging

import tables

from pysparc.muonlab.muonlab_ii import MuonlabII


class Main(object):

    def __init__(self):
        self.muonlab = MuonlabII()
        self.muonlab.select_lifetime_measurement()
        self.muonlab.set_pmt1_voltage(900)
        self.data = tables.openFile('muonlab.h5', 'a')

    def main(self, interval=60, group='lifetime_for_thresholds',
             overwrite=False):
        if group in self.data.root:
            if not overwrite:
                raise RuntimeError("Dataset already exists and overwrite is False")
            else:
                self.data.removeNode('/', group, recursive=True)

        group = self.data.createGroup('/', group)

        print "Taking data... (time interval: %d s)" % interval

        self.muonlab.flush_device()

        for threshold in [10, 30, 50, 70, 90]:
            print threshold,
            self.muonlab.set_pmt1_threshold(threshold)
            t0 = time.time()
            N = 0
            lifetimes = []
            while time.time() - t0 < interval:
                data = self.muonlab.read_lifetime_data()
                N += len(data)
                lifetimes.extend(data)
            self.data.createArray(group, 'threshold_%d' % threshold, lifetimes)
            print N


if __name__ == '__main__':
    logging.basicConfig()

    if 'main' not in globals():
        main = Main()
    main.main(interval=86400)
