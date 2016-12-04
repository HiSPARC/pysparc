import time

from pysparc.muonlab.muonlab_ii import MuonlabII

class Main(object):

    def __init__(self):
        self.muonlab = MuonlabII()
        self.muonlab.select_lifetime_measurement()
        self.muonlab.set_pmt1_voltage(900)

    def main(self):
        for threshold in range(0, 100, 5):
            self.muonlab.set_pmt1_threshold(threshold)
            print threshold,
            self.muonlab.flush_device()
            t0 = time.time()
            while not self.muonlab.read_lifetime_data():
                pass
            dt = time.time() - t0
            print dt


if __name__ == '__main__':
    main = Main()
    main.main()
