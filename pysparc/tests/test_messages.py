import unittest

from mock import patch, sentinel, MagicMock

import pysparc.messages


class HisparcMessageTest(unittest.TestCase):

    def setUp(self):
        self.msg = pysparc.messages.HisparcMessage()

    def test_attributes(self):
        self.assertEqual(self.msg.identifier, None)
        self.assertEqual(self.msg.msg_format, '')
        self.assertEqual(self.msg.data, [])

    def test_encode_returns_none_if_identifier_is_none(self):
        encoded_msg = self.msg.encode()
        self.assertEqual(encoded_msg, None)

    @patch('pysparc.messages.Struct')
    def test_encode_uses_correct_format_if_no_msg_format(self, mock_Struct):
        self.msg.identifier = sentinel.identifier
        self.msg.encode()
        mock_Struct.assert_called_once_with('>BBB')

    @patch('pysparc.messages.Struct')
    def test_encode_uses_correct_format_if_msg_format(self, mock_Struct):
        self.msg.identifier = sentinel.identifier
        self.msg.msg_format = 'FOO'
        self.msg.encode()
        mock_Struct.assert_called_once_with('>BBFOOB')

    @patch('pysparc.messages.Struct')
    @patch.dict('pysparc.messages.codons', {'start': sentinel.start,
                                            'stop': sentinel.stop})
    def test_encode_calls_pack_with_codons(self, mock_Struct):
        self.msg.identifier = sentinel.identifier
        self.msg.encode()
        expected = [sentinel.start, sentinel.identifier, sentinel.stop]
        mock_Struct.return_value.pack.assert_called_once_with(*expected)

    @patch.object(pysparc.messages.HisparcMessage, 'validate_message_start')
    def test_is_message_for_calls_validate_message_start(self,
            mock_validate_message_start):
        buff = MagicMock()
        pysparc.messages.HisparcMessage.is_message_for(buff)
        mock_validate_message_start.assert_called_once_with(buff)

    @patch.object(pysparc.messages.HisparcMessage, 'validate_message_start')
    def test_is_message_for_checks_for_identifier(self,
            mock_validate_message_start):
        buff = MagicMock()
        buff.__getitem__.return_value = sentinel.identifier
        pysparc.messages.HisparcMessage.is_message_for(buff)
        buff.__getitem__.assert_called_once_with(1)

    @patch.object(pysparc.messages.HisparcMessage, 'validate_message_start')
    def test_is_message_for_if_is_match(self,
            mock_validate_message_start):
        buff = MagicMock()
        buff.__getitem__.return_value = sentinel.identifier
        pysparc.messages.HisparcMessage.identifier = sentinel.identifier
        actual = pysparc.messages.HisparcMessage.is_message_for(buff)
        self.assertEqual(actual, True)

    @patch.object(pysparc.messages.HisparcMessage, 'validate_message_start')
    def test_is_message_for_if_no_match(self,
            mock_validate_message_start):
        buff = MagicMock()
        buff.__getitem__.return_value = sentinel.identifier
        pysparc.messages.HisparcMessage.identifier = sentinel.other
        actual = pysparc.messages.HisparcMessage.is_message_for(buff)
        self.assertEqual(actual, False)


if __name__ == '__main__':
    unittest.main()
