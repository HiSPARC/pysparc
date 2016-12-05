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

    def main(self, interval=60, group='lifetime_threshold', overwrite=False):
        if group not in self.data.root:
            self.data.createGroup('/', group)
        group = self.data.getNode('/', group)
        if not overwrite and 'threshold' in group:
            raise RuntimeError("Dataset already exists and overwrite is False")
        elif overwrite:
            self.data.removeNode(group, 'threshold')
            self.data.removeNode(group, 'count')

        print "Taking data... (time interval: %d s)" % interval

        self.muonlab.flush_device()

        thresholds, counts = [], []

        for threshold in range(0, 201, 10):
            print threshold,
            self.muonlab.set_pmt1_threshold(threshold)
            t0 = time.time()
            N = 0
            while time.time() - t0 < interval:
                N += len(self.muonlab.read_lifetime_data())
            thresholds.append(threshold)
            counts.append(N)
            print N

        self.data.createArray(group, 'threshold', thresholds)
        self.data.createArray(group, 'count', counts)


if __name__ == '__main__':
    logging.basicConfig()

    if 'main' not in globals():
        main = Main()
    main.main(interval=3600, group='lifetime_threshold_run2')
