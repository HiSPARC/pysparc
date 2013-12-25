import unittest

from mock import patch, sentinel

from pysparc import util


class UtilTest(unittest.TestCase):

    def test_clipped_map_clips_low(self):
        clipped, mapped = util.clipped_map(0, 1, 10, 10, 100)
        self.assertEqual(clipped, 1)

    def test_clipped_map_clips_high(self):
        clipped, mapped = util.clipped_map(20, 1, 10, 10, 100)
        self.assertEqual(clipped, 10)

    def test_clipped_map_maps_value(self):
        clipped, mapped = util.clipped_map(2, 1, 11, 10, 110)
        self.assertEqual(mapped, 20)

    def test_clipped_map_acceptance(self):
        clipped, mapped = util.clipped_map(100, 300, 1500, 0x00, 0xff)
        self.assertEqual(clipped, 300)
        self.assertEqual(int(mapped), 0x0)

        clipped, mapped = util.clipped_map(2000, 300, 1500, 0x00, 0xff)
        self.assertEqual(clipped, 1500)
        self.assertEqual(int(mapped), 0xff)

        clipped, mapped = util.clipped_map(900, 300, 1500, 0x00, 0xff)
        self.assertEqual(clipped, 900)
        self.assertEqual(int(mapped), 0x7f)

    @patch.object(util, 'clipped_map')
    def test_map_setting_calls_clipped_map(self, mock_map):
        mock_map.return_value = [1.4, 1.5]
        setting = util.map_setting(sentinel.value, 1, 10, 10, 100)
        mock_map.assert_called_once_with(sentinel.value, 1, 10, 10, 100)

    def test_map_setting_returns_int_setting(self):
        setting = util.map_setting(2, 1, 10, 0x0, 0xff)
        self.assertEqual(setting, 0x1c)


if __name__ == '__main__':
    unittest.main()
