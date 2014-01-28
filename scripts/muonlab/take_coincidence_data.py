import time
import logging

from pysparc.muonlab.muonlab_ii import MuonlabII


class Main(object):

    def __init__(self):
        self.muonlab = MuonlabII()
        self.muonlab.select_coincidence_measurement()
        self.muonlab.set_pmt1_voltage(900)
        self.muonlab.set_pmt1_threshold(200)
        self.muonlab.set_pmt2_voltage(1000)
        self.muonlab.set_pmt2_threshold(200)

        self.data = []

    def main(self):
        self.muonlab.flush_device()
        
        t = t0 = time.time()
        l = lt = l0 = len(self.data)
        N = 0

        try:
            while True:
                self.data.extend(self.muonlab.read_coincidence_data())
                N += 1
                if time.time() - t > 1:
                    t = time.time()
                    l = len(self.data)
                    freq = (l - l0) / (t - t0)
                    print int(t - t0), N, freq, l - lt, l, self.data[lt:]
                    lt = l
                    N = 0
        except KeyboardInterrupt:
            return


if __name__ == '__main__':
    logging.basicConfig()

    if 'main' not in globals():
        main = Main()
    main.main()
