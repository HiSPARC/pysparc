import unittest

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

    def test_find_muonlab_in_devices_list(self):
        self.assertIn(MUONLAB_ID, self.devices)


@unittest.skipIf(not hardware_is_present(),
                 "Hardware is not detected, skipping tests.")
class OpenDeviceTest(unittest.TestCase):

    def test_open_device(self):
        device = pylibftdi.Device(DESCRIPTION)


if __name__ == '__main__':
    unittest.main()
