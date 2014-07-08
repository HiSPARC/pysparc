import unittest

from mock import patch, sentinel

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


if __name__ == '__main__':
    unittest.main()
