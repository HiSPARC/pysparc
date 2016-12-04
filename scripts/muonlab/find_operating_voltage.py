import time
import logging

import tables

from pysparc.muonlab.muonlab_ii import MuonlabII


class Main(object):

    def __init__(self):
        self.muonlab = MuonlabII()
        self.muonlab.select_lifetime_measurement()
        self.muonlab.set_pmt1_voltage(300)
        self.muonlab.set_pmt1_threshold(50)
        self.data = tables.openFile('muonlab.h5', 'a')

    def main(self, interval=60, group='operating_voltage', overwrite=False):
        if group not in self.data.root:
            self.data.createGroup('/', group)
        group = self.data.getNode('/', group)
        if not overwrite and 'voltage' in group:
            raise RuntimeError("Dataset already exists and overwrite is False")
        elif overwrite:
            self.data.removeNode(group, 'voltage')
            self.data.removeNode(group, 'count')

        print "Taking data... (time interval: %d s)" % interval

        self.muonlab.flush_device()

        voltages, counts = [], []

        for voltage in range(800, 900, 10):
            print voltage,
            self.muonlab.set_pmt1_voltage(voltage)
            t0 = time.time()
            N = 0
            while time.time() - t0 < interval:
                N += len(self.muonlab.read_lifetime_data())
            voltages.append(voltage)
            counts.append(N)
            print N

        self.data.createArray(group, 'voltage', voltages)
        self.data.createArray(group, 'count', counts)

        self.muonlab.set_pmt1_voltage(300)


if __name__ == '__main__':
    logging.basicConfig()

    if 'main' not in globals():
        main = Main()
    main.main(interval=3600, group='operating_voltage_run5')
