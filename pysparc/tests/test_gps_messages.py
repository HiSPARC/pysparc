import unittest

from mock import patch, sentinel, Mock

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
        # class MockGPSMessage(gps_messages.GPSMessage):
        #
        #     @classmethod
        #     def __subclasses__(cls):
        #         pass
        #
        # patcher1 = patch('pysparc.gps_messages.GPSMessage',
        #                  autospec=MockGPSMessage)

        patcher1 = patch('pysparc.gps_messages.GPSMessage', autospec=True)
        patcher2 = patch('pysparc.gps_messages.find_message_class')
        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)
        self.mock_GPSMessage = patcher1.start()
        self.mock_find_message_class = patcher2.start()

    def test_factory_calls_extract_message_from_buffer(self):
        gps_messages.GPSMessageFactory(sentinel.buffer)
        self.mock_GPSMessage.extract_message_from_buffer\
            .assert_called_once_with(sentinel.buffer)

    def test_factory_calls_find_message_class(self):
        self.mock_GPSMessage.extract_message_from_buffer.return_value = \
            sentinel.msg
        gps_messages.GPSMessageFactory(sentinel.buffer)
        self.mock_find_message_class.assert_called_once_with(
            sentinel.msg, gps_messages.GPSMessage)

    def test_factory_returns_message_instance(self):
        self.mock_GPSMessage.extract_message_from_buffer.return_value = \
            sentinel.msg
        mock_Class = Mock()
        mock_instance = mock_Class.return_value
        self.mock_find_message_class.return_value = mock_Class

        inst = gps_messages.GPSMessageFactory(sentinel.buffer)

        mock_Class.assert_called_once_with(sentinel.msg)
        self.assertIs(inst, mock_instance)

    # def test_factory_calls_all_is_message_for(self):
    #     # msgs = []
    #     # for i in range(3):
    #     #     msgs.append(Mock(autospec=True,
    #     #                      spec='pysparc.gps_messages.GPSMessage'))
    #
    #     self.mock_GPSMessage.__subclasses__ = Mock()
    #     # self.mock_GPSMessage.__subclasses__.return_value = None
    #
    #     gps_messages.GPSMessageFactory(sentinel.buffer)


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
