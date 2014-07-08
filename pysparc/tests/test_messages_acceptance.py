import unittest

import pysparc.messages


class HisparcMessageTest(unittest.TestCase):

    def setUp(self):
        self.msg = pysparc.messages.HisparcMessage()

    def test_encode_if_no_data(self):
        self.msg.identifier = 0xff
        encoded_msg = self.msg.encode()
        expected = str(bytearray([0x99, 0xff, 0x66]))
        self.assertEqual(encoded_msg, expected)

    def test_encode_if_data_and_verify_endianness(self):
        self.msg.identifier = 0xff
        self.msg.msg_format = 'BBH'
        self.msg.data = [0x11, 0x22, 0x33]
        encoded_msg = self.msg.encode()
        expected = str(bytearray([0x99, 0xff, 0x11, 0x22, 0x00, 0x33, 0x66]))
        self.assertEqual(encoded_msg, expected)


if __name__ == '__main__':
    unittest.main()
