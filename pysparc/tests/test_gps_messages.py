import unittest

from mock import patch, sentinel

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


class GPSMessageFactoryTest(unittest.TestCase):

    def setUp(self):
        patcher1 = patch('pysparc.gps_messages.GPSMessage', autospec=True)
        self.addCleanup(patcher1.stop)
        self.mock_GPSMessage = patcher1.start()

    def test_factory_calls_extract_message_from_buffer(self):
        gps_messages.GPSMessageFactory(sentinel.buffer)
        self.mock_GPSMessage.extract_message_from_buffer\
            .assert_called_once_with(sentinel.buffer)

# class GPSMessageFactoryTest(unittest.TestCase):
#
#     def setUp(self):
#         patcher1 = patch('pysparc.gps_messages.GPSMessage', autospec=True)
#         self.addCleanup(patcher1.stop)
#         self.mock_GPSMessage = patcher1.start()
#
#     def test_factory_validates_start_codon(self):
#         gps_messages.GPSMessageFactory(sentinel.msg)
#         self.mock_GPSMessage.validate_message_start.assert_called_once_with(
#             sentinel.msg)
#
#     def test_factory_strips_start_of_message_to_find_start_codon(self):
#         msg = '\x10foo'


if __name__ == '__main__':
    unittest.main()
