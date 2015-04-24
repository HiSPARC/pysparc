import unittest

# from mock import patch, sentinel, MagicMock

from pysparc import messages, gps_messages


class GPSMessageTest(unittest.TestCase):

    def setUp(self):
        self.msg = gps_messages.GPSMessage()

    def test_type_is_BaseMessage(self):
        # This test is VERY important. Do NOT change, without adding lots and
        # lots of tests to make sure everything is still ok. The reason is that
        # we can skip a lot of tests if we know for sure this is a
        # HisparcMessage and the tests for *that* class are ok.
        self.assertIsInstance(self.msg, messages.BaseMessage)

    def test_attributes(self):
        self.assertEqual(self.msg.container_format, '>BB%sH')


if __name__ == '__main__':
    unittest.main()
