import unittest

from mock import patch, sentinel

import pysparc.hardware
import pysparc.storage
import pysparc.events


class TestStoreConfigEventUsingManager(unittest.TestCase):

    @patch('pysparc.hardware.FtdiChip')
    @patch('redis.StrictRedis')
    def test_store_config_event_using_manager(self, mock_redis, mock_ftdi):
        hardware = pysparc.hardware.HiSPARCII()
        manager = pysparc.storage.StorageManager()
        event = pysparc.events.ConfigEvent(sentinel.app_config, hardware.config)

        manager.store_event(event)

        mock_redis.return_value.hmset.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
