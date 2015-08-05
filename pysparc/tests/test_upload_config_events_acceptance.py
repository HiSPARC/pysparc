import unittest

from mock import patch, sentinel

import pysparc.hardware
import pysparc.storage
import pysparc.events


class TestStoreConfigEvent(unittest.TestCase):

    @patch('pysparc.hardware.FtdiChip')
    @patch('redis.StrictRedis')
    def test_store_config_event_succeeds(self, mock_redis, mock_ftdi):
        hardware = pysparc.hardware.HiSPARCII()
        manager = pysparc.storage.StorageManager()
        event = pysparc.events.ConfigEvent(sentinel.app_config, hardware.config)

        manager.store_event(event)


if __name__ == '__main__':
    unittest.main()
