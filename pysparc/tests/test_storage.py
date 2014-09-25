import unittest
import cPickle as pickle

from mock import Mock, patch, sentinel

from pysparc import storage


class StorageWorkerStoreEventTest(unittest.TestCase):

    def setUp(self):
        patcher1 = patch.object(storage.StorageWorker, 'get_event_from_queue')
        patcher2 = patch.object(storage.StorageWorker, 'remove_event_from_queue')
        self.addCleanup(patcher1.stop)
        self.addCleanup(patcher2.stop)

        self.mock_get_event = patcher1.start()
        self.mock_get_event.return_value = sentinel.event, sentinel.key
        self.mock_remove_event = patcher2.start()

        self.mock_datastore = Mock()
        self.worker = storage.StorageWorker(self.mock_datastore,
                                            Mock(), Mock())

    def test_datastore_attribute(self):
        self.assertIs(self.mock_datastore, self.worker.datastore)

    def test_store_event_calls_get_event_from_queue(self):
        self.worker.store_event()
        self.mock_get_event.assert_called_once_with()

    def test_store_event_calls_datastore_if_event(self):
        self.mock_get_event.return_value = None, None
        self.worker.store_event()
        self.assertFalse(self.mock_datastore.store_event.called)

        self.mock_get_event.return_value = sentinel.event, sentinel.key
        self.worker.store_event()
        self.mock_datastore.store_event.assert_called_once_with(sentinel.event)

    def test_store_event_catches_StorageError_but_not_all(self):
        self.mock_datastore.store_event.side_effect = storage.StorageError("Foo")
        self.worker.store_event()

        self.mock_datastore.store_event.side_effect = Exception()
        self.assertRaises(storage.StorageError, self.worker.store_event)

    def test_store_event_calls_remove_event_only_if_no_exception(self):
        self.mock_datastore.store_event.side_effect = storage.StorageError("Foo")
        self.worker.store_event()
        self.assertFalse(self.mock_remove_event.called)

        self.mock_datastore.store_event.side_effect = None
        self.worker.store_event()
        self.mock_remove_event.assert_called_once_with(sentinel.key)


class StorageWorkerKVStoreTest(unittest.TestCase):

    def setUp(self):
        self.mock_kvstore = Mock()
        self.mock_queue = sentinel.queue
        self.worker = storage.StorageWorker(Mock(),
                                            self.mock_kvstore,
                                            self.mock_queue)

    def test_kvstore_attribute(self):
        self.assertIs(self.mock_kvstore, self.worker.kvstore)

    def test_queue_attribute(self):
        self.assertIs(self.mock_queue, self.worker.queue)

    @patch('cPickle.loads')
    def test_get_event_from_queue(self, mock_pickle_loads):
        pickled_event = pickle.dumps(sentinel.event)
        self.mock_kvstore.lindex.return_value = sentinel.key
        self.mock_kvstore.hget.return_value = pickled_event
        mock_pickle_loads.return_value = sentinel.event

        event, key = self.worker.get_event_from_queue()

        # get first event key from queue
        self.mock_kvstore.lindex.assert_called_once_with(self.mock_queue, 0)
        # get 'event' from event key (is pickled event)
        self.mock_kvstore.hget.assert_called_once_with(sentinel.key, 'event')
        # unpickle event
        mock_pickle_loads.assert_called_once_with(pickled_event)
        # check return values
        self.assertIs(key, sentinel.key)
        self.assertIs(event, sentinel.event)

    def test_remove_event_from_queue_removes_from_queue_and_decr_counter(self):
        self.mock_kvstore.lpop.return_value = sentinel.key

        self.worker.remove_event_from_queue(sentinel.key)

        # remove first element from queue
        self.mock_kvstore.lpop.assert_called_once_with(self.mock_queue)
        # decrease event counter
        self.mock_kvstore.hincrby.assert_called_once_with(sentinel.key, 'count', -1)

    def test_remove_event_from_queue_removes_event_only_if_counter_zero(self):
        self.mock_kvstore.lpop.return_value = sentinel.key
        
        self.mock_kvstore.hincrby.return_value = 1
        self.worker.remove_event_from_queue(sentinel.key)
        self.assertFalse(self.mock_kvstore.delete.called)

        self.mock_kvstore.hincrby.return_value = 0
        self.worker.remove_event_from_queue(sentinel.key)
        self.mock_kvstore.delete.assert_called_once_with(sentinel.key)

    def test_remove_event_from_queue_raises_IntegrityError(self):
        self.mock_kvstore.lpop.return_value = sentinel.other_key

        self.assertRaises(storage.IntegrityError, self.worker.remove_event_from_queue, sentinel.key)


if __name__ == '__main__':
    unittest.main()
