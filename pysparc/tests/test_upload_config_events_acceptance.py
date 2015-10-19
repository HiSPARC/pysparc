import unittest

from mock import patch, sentinel

import pysparc.hardware
import pysparc.storage
import pysparc.events


class TestStoreConfigEvent(unittest.TestCase):

    @patch('pysparc.hardware.FtdiChip')
    @patch('redis.StrictRedis')
    def test_if_manager_succeeds(self, mock_redis, mock_ftdi):
        hardware = pysparc.hardware.HiSPARCII()
        manager = pysparc.storage.StorageManager()
        event = pysparc.events.ConfigEvent(hardware.config)

        manager.store_event(event)

    @patch('pysparc.hardware.FtdiChip')
    @patch('pysparc.storage.NikhefDataStore._upload_data')
    def test_if_datastore_succeeds(self, mock_upload, mock_ftdi):
        hardware = pysparc.hardware.HiSPARCII()
        datastore = pysparc.storage.NikhefDataStore(sentinel.station_id,
                                                    sentinel.password)
        event = pysparc.events.ConfigEvent(hardware.config)

        datastore.store_event(event)

if __name__ == '__main__':
    unittest.main()
