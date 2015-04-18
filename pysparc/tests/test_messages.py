import unittest

from mock import patch, sentinel, MagicMock

import pysparc.messages


class HisparcMessageTest(unittest.TestCase):

    def setUp(self):
        self.msg = pysparc.messages.HisparcMessage()

    def test_attributes(self):
        self.assertEqual(self.msg.identifier, None)
        self.assertEqual(self.msg.container_format, '>BB%sB')
        self.assertEqual(self.msg.msg_format, '')
        self.assertEqual(self.msg.data, [])

    def test_encode_returns_none_if_identifier_is_none(self):
        encoded_msg = self.msg.encode()
        self.assertEqual(encoded_msg, None)

    @patch('pysparc.messages.struct.Struct')
    def test_encode_uses_correct_format_if_no_msg_format(self, mock_Struct):
        self.msg.container_format = 'Foo%sbar'
        self.msg.msg_format = ''
        self.msg.identifier = sentinel.identifier
        self.msg.encode()
        mock_Struct.assert_called_once_with('Foobar')

    @patch('pysparc.messages.struct.Struct')
    def test_encode_uses_correct_format_if_msg_format(self, mock_Struct):
        self.msg.identifier = sentinel.identifier
        self.msg.container_format = 'Foo%sbar'
        self.msg.msg_format = 'baz'
        self.msg.encode()
        mock_Struct.assert_called_once_with('Foobazbar')

    @patch('pysparc.messages.struct.Struct')
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
    @patch.object(pysparc.messages.HisparcMessage, 'identifier')
    def test_is_message_for_if_is_match(self, mock_identifier,
            mock_validate_message_start):
        buff = MagicMock()
        buff.__getitem__.return_value = mock_identifier
        actual = pysparc.messages.HisparcMessage.is_message_for(buff)
        self.assertEqual(actual, True)

    @patch.object(pysparc.messages.HisparcMessage, 'validate_message_start')
    @patch.object(pysparc.messages.HisparcMessage, 'identifier')
    def test_is_message_for_if_no_match(self, mock_identifier,
            mock_validate_message_start):
        buff = MagicMock()
        buff.__getitem__.return_value = sentinel.other_identifier
        actual = pysparc.messages.HisparcMessage.is_message_for(buff)
        self.assertEqual(actual, False)

    def test_validate_message_start_checks_first_byte(self):
        buff = MagicMock()
        try:
            pysparc.messages.HisparcMessage.validate_message_start(buff)
        except:
            pass
        buff.__getitem__.assert_called_once_with(0)

    def test_validate_message_start_raises_StartCodonError_if_not_start_codon(self):
        self.assertRaises(pysparc.messages.StartCodonError,
            pysparc.messages.HisparcMessage.validate_message_start, [0x00])

    def test_validate_message_start_passes_if_match(self):
        buff = [pysparc.messages.codons['start']]
        pysparc.messages.HisparcMessage.validate_message_start(buff)

    def test_validate_codons_and_id(self):
        codons = pysparc.messages.codons
        start, identifier, stop = codons['start'], 0x11, codons['stop']
        self.msg.identifier = identifier
        self.assertRaises(pysparc.messages.MessageError,
                          self.msg.validate_codons_and_id,
                          0x00, identifier, stop)
        self.assertRaises(pysparc.messages.MessageError,
                          self.msg.validate_codons_and_id,
                          start, 0x00, stop)
        self.assertRaises(pysparc.messages.MessageError,
                          self.msg.validate_codons_and_id,
                          start, identifier, 0x00)
        self.msg.validate_codons_and_id(start, identifier, stop)


class SetControlParameterTest(unittest.TestCase):

    def setUp(self):
        self.msg_ids_patcher = patch.object(pysparc.messages, 'msg_ids')
        self.mock_msg_ids = self.msg_ids_patcher.start()

    def tearDown(self):
        self.msg_ids_patcher.stop()

    def test_identifier(self):
        msg = pysparc.messages.SetControlParameter(sentinel.parameter,
            sentinel.value)
        self.mock_msg_ids.__getitem__.assert_called_once_with(sentinel.parameter)
        self.assertEqual(msg.identifier, self.mock_msg_ids.__getitem__.return_value)

    def test_data(self):
        msg = pysparc.messages.SetControlParameter(sentinel.parameter,
            sentinel.value)
        self.assertEqual(msg.data, [sentinel.value])

    def test_msg_format_for_nbytes_is_1(self):
        msg = pysparc.messages.SetControlParameter(sentinel.parameter,
            sentinel.value, nbytes=1)
        self.assertEqual(msg.msg_format, 'B')

    def test_msg_format_for_nbytes_is_2(self):
        msg = pysparc.messages.SetControlParameter(sentinel.parameter,
            sentinel.value, nbytes=2)
        self.assertEqual(msg.msg_format, 'H')

    def test_msg_format_raises_NotImplementedError(self):
        self.assertRaises(NotImplementedError,
                          pysparc.messages.SetControlParameter,
                          sentinel.parameter, sentinel.value, nbytes=4)


class InitializeMessageTest(unittest.TestCase):

    def test_identifier(self):
        self.assertEqual(pysparc.messages.InitializeMessage.identifier,
                         pysparc.messages.msg_ids['spare_bytes'])

    def test_msg_format(self):
        self.assertEqual(pysparc.messages.InitializeMessage.msg_format,
                         'I')

    def test_data_if_one_second_messages_disabled(self):
        msg = pysparc.messages.InitializeMessage(False)
        self.assertEqual(msg.data, [0b101])

    def test_data_if_one_second_messages_enabled(self):
        msg = pysparc.messages.InitializeMessage(True)
        self.assertEqual(msg.data, [0b111])


class ResetMessageTest(unittest.TestCase):

    def test_identifier(self):
        self.assertEqual(pysparc.messages.ResetMessage.identifier,
                         pysparc.messages.msg_ids['reset'])


if __name__ == '__main__':
    unittest.main()
