import unittest

# from mock import patch, sentinel, MagicMock

from pysparc import messages, gps_messages


class GPSMessageTest(unittest.TestCase):

    def setUp(self):
        self.msg = gps_messages.GPSMessage()

    def test_type_is_HisparcMessage(self):
        self.assertIsInstance(self.msg, messages.HisparcMessage)

    def test_attributes(self):
        self.assertEqual(self.msg.container_format, '>BB%sH')


if __name__ == '__main__':
    unittest.main()
