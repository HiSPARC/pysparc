import logging
import unittest

from mock import patch, sentinel, Mock, MagicMock, create_autospec

from pysparc import messages, gps_messages


class GPSMessageTest(unittest.TestCase):

    def setUp(self):
        self.msg = gps_messages.GPSMessage()

    def test_type_is_BaseMessage(self):
        # This test is VERY important. Do NOT change, without adding lots and
        # lots of tests to make sure everything is still ok. The reason is that
        # we can skip a lot of tests if we know for sure this is a
        # BaseMessage and the tests for *that* class are ok.
        self.assertIsInstance(self.msg, messages.BaseMessage)

    def test_attributes(self):
        self.assertEqual(self.msg.container_format, '>BB%sH')

    def test_extract_message_from_buffer(self):
        func = gps_messages.GPSMessage.extract_message_from_buffer
        # just one message
        self.assertEqual(func(bytearray('\x10foo\x10\x03')),
                         'foo')
        # one message with extra characters
        self.assertEqual(func(bytearray('\x10foo\x10\x03bar')),
                         'foo')
        # two messages, extract ONE
        self.assertEqual(func(bytearray('\x10foo\x10\x03\x10bar\x10\x03')),
                         'foo')
        # escaped characters, squash them
        self.assertEqual(func(bytearray('\x10foo\x10\x10bar\x10\x03')),
                         'foo\x10bar')
        # escaped characters, squash them
        self.assertEqual(func(bytearray('\x10foo\x10\x10\x10\x10bar\x10\x03')),
                         'foo\x10\x10bar')
        # escaped stop codon, so incomplete message
        self.assertEqual(func(bytearray('\x10foo\x10\x10\x03')),
                         None)
        # escaped first stop codon, complete message
        self.assertEqual(func(bytearray('\x10foo\x10\x10\x03\x10\x03')),
                         'foo\x10\x03')
        # message with garbage at front
        self.assertEqual(func(bytearray('baz\x10foo\x10\x03')),
                         'foo')
        # message with garbage at front, no start codon
        self.assertEqual(func(bytearray('baz')),
                         None)

    def test_extract_message_from_buffer_deletes_from_buffer(self):
        buff = bytearray('\x10foo\x10\x03barbaz')
        gps_messages.GPSMessage.extract_message_from_buffer(buff)
        self.assertEqual(buff, 'barbaz')

    @patch.object(gps_messages.GPSMessage, 'identifier')
    def test_is_message_for(self, identifier):
        msg = create_autospec(str)
        msg.startswith.return_value = sentinel.value

        actual = gps_messages.GPSMessage.is_message_for(msg)

        msg.startswith.assert_called_once_with(identifier)
        self.assertEqual(actual, sentinel.value)


class GPSMessageFactoryTest(unittest.TestCase):

    def setUp(self):
        patcher1 = patch('pysparc.gps_messages.GPSMessage')
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

    def test_factory_return_none_if_no_message(self):
        self.mock_GPSMessage.extract_message_from_buffer.return_value = \
            None
        actual = gps_messages.GPSMessageFactory(sentinel.buffer)
        self.assertFalse(self.mock_find_message_class.called)
        self.assertIsNone(actual)

    def test_factory_returns_message_instance(self):
        self.mock_GPSMessage.extract_message_from_buffer.return_value = \
            sentinel.msg
        mock_Class = Mock()
        mock_instance = mock_Class.return_value
        self.mock_find_message_class.return_value = mock_Class

        inst = gps_messages.GPSMessageFactory(sentinel.buffer)

        mock_Class.assert_called_once_with(sentinel.msg)
        self.assertIs(inst, mock_instance)

    def test_factory_catches_UnknownMessageError(self):
        self.mock_find_message_class.side_effect = \
            gps_messages.UnknownMessageError

        actual = gps_messages.GPSMessageFactory(sentinel.buffer)

        self.assertIsNone(actual)


class FindMessageForTest(unittest.TestCase):

    class MockGPSMessage(gps_messages.GPSMessage):

        __subclasses__ = Mock()

    def test_find_message_class_calls_all_is_message_for_and_raises(self):
        msgs = []
        for i in range(3):
            msg = create_autospec(gps_messages.GPSMessage)
            msg.is_message_for.return_value = False
            msgs.append(msg)
        self.MockGPSMessage.__subclasses__.return_value = msgs
        mock_msg = MagicMock()

        self.assertRaises(gps_messages.UnknownMessageError,
                          gps_messages.find_message_class, mock_msg,
                          self.MockGPSMessage)

        for msg in msgs:
            msg.is_message_for.assert_called_once_with(mock_msg)

    def test_find_message_class_returns_instance(self):
        Msg = Mock()
        Msg.is_message_for.return_value = True
        Msg.return_value = sentinel.instance
        self.MockGPSMessage.__subclasses__.return_value = [Msg]

        actual = gps_messages.find_message_class(sentinel.msg,
                                                 self.MockGPSMessage)

        Msg.assert_called_once_with(sentinel.msg)
        self.assertEqual(actual, sentinel.instance)


if __name__ == '__main__':
    logging.basicConfig(level=logging.CRITICAL)
    unittest.main()
