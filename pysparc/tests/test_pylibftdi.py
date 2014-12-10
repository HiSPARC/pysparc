import unittest
import time

import pylibftdi


class DeviceReadTest(unittest.TestCase):

    def test_read_timeout(self):
        # on Linux, there is a strange bug that sets the timeout to zero.
        # However, after sleep, with the FTDI device still plugged in *and
        # used at least once*, the timeout kicks in and the effective
        # timeout will be the 16 ms promised by a timeout inside the FTDI
        # chip.
        #
        # Test that the timeout is 16 ms, not less.  We expect to not see
        # data, so the PMT voltages must be zero!

        try:
            device = pylibftdi.Device()
        except pylibftdi.FtdiError:
            self.skipTest("Device not found")

        device.flush()
        t = []
        for i in range(10):
            t0 = time.time()
            device.read(62)
            t.append(time.time() - t0)
        mean_t = sum(t) / len(t)
        self.assertAlmostEqual(mean_t, 16e-3, delta=2e-3)


if __name__ == '__main__':
    unittest.main()
