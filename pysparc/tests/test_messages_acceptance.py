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


class InitializeMessageTest(unittest.TestCase):

    def test_encoded_msg_if_one_second_enabled(self):
        msg = pysparc.messages.InitializeMessage(True)
        expected = str(bytearray([0x99, 0x35, 0x00, 0x00, 0x00, 0x07, 0x66]))
        actual = msg.encode()
        self.assertEqual(actual, expected)

    def test_encoded_msg_if_one_second_disabled(self):
        msg = pysparc.messages.InitializeMessage(False)
        expected = str(bytearray([0x99, 0x35, 0x00, 0x00, 0x00, 0x05, 0x66]))
        actual = msg.encode()
        self.assertEqual(actual, expected)


class ResetMessageTest(unittest.TestCase):

    def test_encoded_msg(self):
        msg = pysparc.messages.ResetMessage()
        expected = str(bytearray([0x99, 0xff, 0x66]))
        actual = msg.encode()
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()
