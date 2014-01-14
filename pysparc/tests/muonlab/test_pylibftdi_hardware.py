import unittest
import time

import pylibftdi


MANUFACTURER = 'FTDI'
DESCRIPTION = 'USB <-> Serial'
SERIAL_NUM = ''
MUONLAB_ID = (MANUFACTURER, DESCRIPTION, SERIAL_NUM)

hardware_is_present = lambda: MUONLAB_ID in \
    pylibftdi.Driver().list_devices()


class ListDevicesTest(unittest.TestCase):

    def setUp(self):
        self.driver = pylibftdi.Driver()
        self.devices = self.driver.list_devices()

    def test_list_devices_returns_list(self):
        self.assertIsInstance(self.devices, list)

    @unittest.expectedFailure
    def test_find_muonlab_in_devices_list(self):
        self.assertIn(MUONLAB_ID, self.devices)


@unittest.skipIf(not hardware_is_present(),
                 "Hardware is not detected, skipping tests.")
class OpenDeviceTest(unittest.TestCase):

    def test_open_device(self):
        device = pylibftdi.Device(DESCRIPTION)

    def test_read_timeout(self):
        # on Linux, there is a strange bug that sets the timeout to zero.
        # However, after sleep, with the FTDI device still plugged in *and
        # used at least once*, the timeout kicks in and the effective
        # timeout will be the 16 ms promised by a timeout inside the FTDI
        # chip.
        #
        # Test that the timeout is 16 ms, not less.  We expect to not see
        # data, so the PMT voltages must be zero!

        device = pylibftdi.Device(DESCRIPTION)
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
